"""Bounded, keyless official-source access: GovInfo allowlist and the Federal Register API (§6.5).

* URLs are built by TraID only, from validated FR JSON fields (publication date D, document number
  N); never from claim text, document content, FR JSON URL fields or redirects.
* Redirects are never followed; status must be exactly 200; content types are exact; bodies are
  streamed with size caps. Every failure is an explicit ``SOURCE_UNAVAILABLE:*`` outcome, never an
  exception and never a retry. No API key, email or contact header is ever sent.
* Requests are sequential and counted against a fixed per-client budget.

Federal Register rate limits are undocumented to TraID (FEDERAL_REGISTER_RATE_LIMITS_UNDOCUMENTED).
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from http.client import HTTPException, IncompleteRead
import json
import re
import socket
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from pydantic import ValidationError

from traid.news.models import (
    DocketListing, FrMetadataRecord, FrPublicInspectionRecord, GovInfoHtml, GovInfoModsRetrieval, GovInfoPdf,
    sha256_hex, utc,
)
from traid.news.text import canonical_file_number

UTC = timezone.utc
GOVINFO_HOST = "www.govinfo.gov"
FR_HOST = "www.federalregister.gov"
USER_AGENT = "TraID primary-source verification (read-only)"
DOCNO = r"(?P<n>\d{4}-\d{5})"
PKG = r"FR-(?P<d>\d{4}-\d{2}-\d{2})"
GOVINFO_PATHS = {
    "PDF": re.compile(rf"^/content/pkg/{PKG}/pdf/{DOCNO}\.pdf$"),
    "HTML": re.compile(rf"^/content/pkg/{PKG}/html/{DOCNO}\.htm$"),
    "MODS": re.compile(rf"^/metadata/granule/{PKG}/{DOCNO}/mods\.xml$"),
}
CONTENT_TYPES = {"PDF": ("application/pdf",), "HTML": ("text/html",), "MODS": ("text/xml", "application/xml"),
                 "FR_JSON": ("application/json",)}
MAX_BYTES = {"PDF": 20 * 2**20, "HTML": 8 * 2**20, "MODS": 1 * 2**20, "FR_JSON": 4 * 2**20}
DEFAULT_BUDGET = 20
SEC_AGENCY = "securities-and-exchange-commission"


# ---------------------------------------------------------------------- URL allowlist
def govinfo_url(kind: str, publication_date: date, document_number: str) -> str:
    d = publication_date.isoformat()
    path = {"PDF": f"/content/pkg/FR-{d}/pdf/{document_number}.pdf",
            "HTML": f"/content/pkg/FR-{d}/html/{document_number}.htm",
            "MODS": f"/metadata/granule/FR-{d}/{document_number}/mods.xml"}[kind]
    return f"https://{GOVINFO_HOST}{path}"


def validate_govinfo_url(url: str, kind: str, publication_date: date, document_number: str,
                         origin: str = "CONSTRUCTED") -> str:
    """OK, or the specific rejection reason. Applied before any request."""
    if origin != "CONSTRUCTED":
        return "URL_NOT_CONSTRUCTED_BY_TRAID"
    if not isinstance(url, str) or not url.isascii() or any(c in url for c in "\\%@ \t\r\n") \
            or any(ord(c) < 0x20 or ord(c) == 0x7f for c in url):
        return "URL_CHARACTERS_REJECTED"
    parts = urlsplit(url)
    if parts.scheme != "https":
        return "URL_SCHEME_NOT_HTTPS"
    if parts.netloc != GOVINFO_HOST:
        return "URL_HOST_NOT_ALLOWED"
    if parts.query or parts.fragment or url.endswith("?") or "#" in url:
        return "URL_QUERY_OR_FRAGMENT_REJECTED"
    if "//" in parts.path or "/./" in parts.path or "/../" in parts.path or parts.path.endswith(("/.", "/..")):
        return "URL_PATH_TRAVERSAL_REJECTED"
    m = GOVINFO_PATHS[kind].match(parts.path)
    if m is None:
        return "URL_PATH_NOT_ALLOWED"
    try:
        package_date = date.fromisoformat(m.group("d"))
    except ValueError:
        return "URL_PACKAGE_DATE_INVALID"
    if package_date != publication_date:
        return "URL_PACKAGE_DATE_MISMATCH"
    if m.group("n") != document_number:
        return "URL_DOCUMENT_NUMBER_MISMATCH"
    if url != govinfo_url(kind, publication_date, document_number):
        return "URL_NOT_CANONICAL"
    return "OK"


def fr_document_url(document_number: str) -> str:
    return f"https://{FR_HOST}/api/v1/documents/{document_number}.json"


def fr_public_inspection_url(document_number: str) -> str:
    return f"https://{FR_HOST}/api/v1/public-inspection-documents/{document_number}.json"


def fr_docket_url(file_number: str, page: int = 1) -> str:
    fields = "".join(f"&fields%5B%5D={f}" for f in ("document_number", "publication_date", "docket_ids", "correction_of"))
    return (f"https://{FR_HOST}/api/v1/documents.json?per_page=100&order=oldest&page={page}"
            f"&conditions%5Bdocket_id%5D={file_number}{fields}")


# ------------------------------------------------------------------ response acceptance
@dataclass(frozen=True)
class HttpResponse:
    """The origin's final response (a proxy CONNECT preamble is never a status)."""
    status: int
    headers: Mapping[str, str] = field(default_factory=dict)   # lower-case names
    body: bytes | None = None
    timed_out: bool = False
    truncated: bool = False         # the body exceeded the cap and was not read further
    failure: str | None = None      # transport failure without a response


CHUNKED = "CHUNKED"
PROTOCOL_ERROR = "HTTP_PROTOCOL_ERROR"


def framing(headers) -> int | str | None:
    """How the body is delimited, from every header line (a mapping or the raw (name, value) pairs):
    CHUNKED, the declared fixed length, None (delimited by connection close), or PROTOCOL_ERROR.

    The only transfer coding supported is a single ``Transfer-Encoding: chunked`` line, matched exactly as
    http.client matches it (``value.lower() == "chunked"``), so TraID and the transport never disagree on
    framing. Anything else (a compound or unknown coding, a repeated line, chunked with Content-Length,
    conflicting or malformed Content-Length) fails closed: no other decoding contract is verified."""
    items = list(headers.items()) if isinstance(headers, Mapping) else list(headers)
    codings = [v for k, v in items if k.lower() == "transfer-encoding"]
    lengths = [v for k, v in items if k.lower() == "content-length"]
    if codings:
        if len(codings) != 1 or codings[0].lower() != "chunked" or lengths:   # RFC 9112 §6.3
            return PROTOCOL_ERROR
        return CHUNKED                  # a truncated chunked stream raises IncompleteRead
    if not lengths:
        return None
    if len({v.strip() for v in lengths}) != 1:
        return PROTOCOL_ERROR
    value = lengths[0].strip()
    return int(value) if re.fullmatch(r"[0-9]{1,15}", value) else PROTOCOL_ERROR


def length_problem(headers, received: int) -> str | None:
    """A completed fixed-length body must have exactly the declared length (a premature EOF is incomplete)."""
    declared = framing(headers)
    if declared == PROTOCOL_ERROR:
        return PROTOCOL_ERROR
    if declared is None or declared == CHUNKED or received == declared:
        return None
    return "INCOMPLETE_READ" if received < declared else "CONTENT_LENGTH_MISMATCH"


def accept_response(kind: str, response: HttpResponse) -> str:
    """Bounded retrieval: no redirect followed, exact status and content type, size cap; fail closed."""
    if response.timed_out:
        return "SOURCE_UNAVAILABLE:TIMEOUT"
    if response.failure is not None:
        return f"SOURCE_UNAVAILABLE:{response.failure}"
    if 300 <= response.status < 400:
        return f"SOURCE_UNAVAILABLE:REDIRECT_NOT_FOLLOWED:{response.headers.get('location', '')}"
    if response.status != 200:
        return f"SOURCE_UNAVAILABLE:HTTP_{response.status}"
    ctype = response.headers.get("content-type", "").split(";")[0].strip().lower()
    if ctype not in CONTENT_TYPES[kind]:
        return f"SOURCE_UNAVAILABLE:CONTENT_TYPE:{ctype or 'missing'}"
    if response.truncated or (response.body is not None and len(response.body) > MAX_BYTES[kind]):
        return "SOURCE_UNAVAILABLE:RESPONSE_TOO_LARGE"
    if response.body is None:
        return "SOURCE_UNAVAILABLE:EMPTY"
    problem = length_problem(response.headers, len(response.body))    # also for an injected transport
    if problem is not None:
        return f"SOURCE_UNAVAILABLE:{problem}"
    return "OK"


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None   # urllib then raises HTTPError with the 3xx status; the redirect is never followed


def http_get(url: str, *, cap: int, timeout: float) -> HttpResponse:
    """Default transport: one GET, no redirects, streamed up to ``cap`` + 1 bytes."""
    opener = build_opener(_NoRedirect())
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"}, method="GET")
    try:
        with opener.open(request, timeout=timeout) as response:
            raw = list(response.headers.items())                  # every line, repeated ones included
            headers = {k.lower(): v for k, v in raw}
            declared = framing(raw)
            transport_chunked = getattr(response, "chunked", declared == CHUNKED)
            if declared == PROTOCOL_ERROR or transport_chunked is not (declared == CHUNKED):
                return HttpResponse(status=0, failure=PROTOCOL_ERROR)  # nothing is read
            if isinstance(declared, int) and declared > cap:
                return HttpResponse(status=response.status, headers=headers, truncated=True)
            chunks, size = [], 0
            while size <= cap:
                chunk = response.read(min(65536, cap + 1 - size))
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
            if size > cap:          # never read further than cap + 1 bytes
                return HttpResponse(status=response.status, headers=headers, body=b"".join(chunks), truncated=True)
            # read(amt) returns b"" at a premature EOF instead of raising: the partial body is discarded
            problem = length_problem(raw, size)
            if problem is not None:
                return HttpResponse(status=0, failure=problem)
            return HttpResponse(status=response.status, headers=headers, body=b"".join(chunks))
    except HTTPError as error:
        return HttpResponse(status=error.code, headers={k.lower(): v for k, v in (error.headers or {}).items()})
    except (socket.timeout, TimeoutError):
        return HttpResponse(status=0, timed_out=True)
    except IncompleteRead:              # body shorter than announced: the partial bytes are discarded
        return HttpResponse(status=0, failure="INCOMPLETE_READ")
    except HTTPException:               # malformed status line, headers or chunking
        return HttpResponse(status=0, failure="HTTP_PROTOCOL_ERROR")
    except (URLError, OSError) as error:
        reason = getattr(error, "reason", None)
        if isinstance(reason, (socket.timeout, TimeoutError)):
            return HttpResponse(status=0, timed_out=True)
        return HttpResponse(status=0, failure="CONNECTION_FAILED")


Transport = Callable[[str, int, float], HttpResponse]


@dataclass(frozen=True)
class Fetched:
    """A component retrieval or the reason it is absent (the document then cannot qualify)."""
    record: Any = None
    reason: str | None = None
    limitations: tuple[str, ...] = ()


class _Budgeted:
    def __init__(self, *, timeout: float, budget: int, clock: Callable[[], datetime] | None,
                 transport: Transport | None) -> None:
        if timeout <= 0 or budget <= 0:
            raise ValueError("timeout and budget must be positive")
        self.timeout = timeout
        self.remaining = budget
        self._clock = clock or (lambda: datetime.now(tz=UTC))
        self._transport = transport or (lambda url, cap, timeout: http_get(url, cap=cap, timeout=timeout))

    def _get(self, url: str, kind: str) -> tuple[HttpResponse | None, datetime | None, str]:
        if self.remaining <= 0:
            return None, None, "SOURCE_UNAVAILABLE:REQUEST_BUDGET_EXHAUSTED"
        self.remaining -= 1
        try:
            response = self._transport(url, MAX_BYTES[kind], self.timeout)
        except (socket.timeout, TimeoutError):       # an injected transport that raises still fails closed
            response = HttpResponse(status=0, timed_out=True)
        except IncompleteRead:
            response = HttpResponse(status=0, failure="INCOMPLETE_READ")
        except HTTPException:
            response = HttpResponse(status=0, failure="HTTP_PROTOCOL_ERROR")
        except OSError:
            response = HttpResponse(status=0, failure="CONNECTION_FAILED")
        received = self._clock()
        if not isinstance(received, datetime) or received.tzinfo is None or received.utcoffset() is None:
            raise ValueError("clock must return an aware datetime")
        return response, received.astimezone(UTC), accept_response(kind, response)


class GovInfoClient(_Budgeted):
    """GovInfo content and granule MODS only (closed allowlist); no API, no key."""

    def __init__(self, *, timeout: float = 30.0, budget: int = DEFAULT_BUDGET,
                 clock: Callable[[], datetime] | None = None, transport: Transport | None = None) -> None:
        super().__init__(timeout=timeout, budget=budget, clock=clock, transport=transport)

    def fetch(self, kind: str, metadata: FrMetadataRecord) -> Fetched:
        D, N = metadata.publication_date, metadata.document_number
        url = govinfo_url(kind, D, N)
        why = validate_govinfo_url(url, kind, D, N)
        if why != "OK":
            return Fetched(reason=why)
        response, received, why = self._get(url, kind)
        if why != "OK":
            return Fetched(reason=why)
        body = response.body
        common = dict(document_number=N, url=url, retrieved_at=received, sha256=sha256_hex(body), byte_length=len(body))
        if kind == "PDF":
            return Fetched(record=GovInfoPdf(**common))   # bytes are not kept: content comes only from a human record
        if kind == "HTML":
            return Fetched(record=GovInfoHtml(**common, body=body))
        return Fetched(record=GovInfoModsRetrieval(**common, body=body))


# --------------------------------------------------------------- Federal Register JSON
def _text(value) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("non-empty text required")
    return value


def _strings(value) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(x, str) for x in value):
        raise ValueError("list of strings required")
    return tuple(value)


def parse_fr_document(body: bytes, *, requested: str, source_url: str, retrieved_at: datetime) -> FrMetadataRecord | str:
    """Federal Register API document JSON to a metadata record, or SOURCE_UNAVAILABLE:MALFORMED_*."""
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return "SOURCE_UNAVAILABLE:MALFORMED_JSON"
    try:
        if not isinstance(payload, dict):
            raise ValueError("object required")
        if payload.get("document_number") != requested:
            return "SOURCE_UNAVAILABLE:DOCUMENT_NUMBER_MISMATCH"
        agencies = payload.get("agencies")
        if not isinstance(agencies, list):
            raise ValueError("agencies required")
        corrections = payload.get("corrections") or []
        for key in ("volume", "start_page", "end_page"):
            if type(payload.get(key)) is not int:
                raise ValueError(f"{key} must be an integer")
        return FrMetadataRecord(
            document_number=payload["document_number"], citation=_text(payload.get("citation")),
            volume=payload["volume"], start_page=payload["start_page"], end_page=payload["end_page"],
            publication_date=date.fromisoformat(_text(payload.get("publication_date"))),
            document_type=_text(payload.get("type")),
            agency_slugs=tuple(sorted(str(a.get("slug")) for a in agencies if isinstance(a, dict) and a.get("slug"))),
            docket_ids=_strings(payload.get("docket_ids")), title=_text(payload.get("title")),
            correction_of=payload.get("correction_of") if isinstance(payload.get("correction_of"), str) else None,
            corrections=tuple(str(c) for c in corrections) if isinstance(corrections, list) else ("UNPARSEABLE",),
            pdf_url=payload.get("pdf_url") if isinstance(payload.get("pdf_url"), str) else None,
            mods_url=payload.get("mods_url") if isinstance(payload.get("mods_url"), str) else None,
            source_url=source_url, retrieved_at=retrieved_at, payload_digest=sha256_hex(body))
    except (KeyError, TypeError, ValueError, ValidationError):
        return "SOURCE_UNAVAILABLE:MALFORMED_METADATA"


def parse_fr_public_inspection(body: bytes, *, requested: str, source_url: str,
                               retrieved_at: datetime) -> FrPublicInspectionRecord | str:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return "SOURCE_UNAVAILABLE:MALFORMED_JSON"
    try:
        if not isinstance(payload, dict) or payload.get("document_number") != requested:
            return "SOURCE_UNAVAILABLE:DOCUMENT_NUMBER_MISMATCH"
        filed = _text(payload.get("filed_at"))
        return FrPublicInspectionRecord(document_number=requested, filed_at=utc(filed, "filed_at"), filed_at_source=filed,
                                        source_url=source_url, retrieved_at=retrieved_at, payload_digest=sha256_hex(body))
    except (KeyError, TypeError, ValueError, ValidationError):
        return "SOURCE_UNAVAILABLE:MALFORMED_METADATA"


def parse_fr_docket_page(body: bytes) -> tuple[int, tuple[str, ...], bool] | str:
    """(count, document numbers on the page, has a next page) of one docket listing page."""
    try:
        payload = json.loads(body.decode("utf-8"))
        count = payload["count"]
        results = payload.get("results") or []
        if type(count) is not int or not isinstance(results, list):
            raise ValueError("count and results required")
        numbers = tuple(_text(r["document_number"]) for r in results)
        return count, numbers, bool(payload.get("next_page_url"))
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return "SOURCE_UNAVAILABLE:MALFORMED_JSON"


class FederalRegisterClient(_Budgeted):
    """Federal Register API (keyless): document metadata, public-inspection records, docket listings."""

    def __init__(self, *, timeout: float = 15.0, budget: int = DEFAULT_BUDGET,
                 clock: Callable[[], datetime] | None = None, transport: Transport | None = None) -> None:
        super().__init__(timeout=timeout, budget=budget, clock=clock, transport=transport)

    def document(self, document_number: str) -> Fetched:
        if not re.fullmatch(r"\d{4}-\d{5}", document_number or ""):
            return Fetched(reason="DOCUMENT_NUMBER_INVALID")
        url = fr_document_url(document_number)
        response, received, why = self._get(url, "FR_JSON")
        if why != "OK":
            return Fetched(reason=why, limitations=("FEDERAL_REGISTER_RATE_LIMITS_UNDOCUMENTED",))
        parsed = parse_fr_document(response.body, requested=document_number, source_url=url, retrieved_at=received)
        if isinstance(parsed, str):
            return Fetched(reason=parsed)
        if SEC_AGENCY not in parsed.agency_slugs:
            return Fetched(record=parsed, limitations=("NOT_AN_SEC_DOCUMENT",))
        return Fetched(record=parsed, limitations=("FEDERAL_REGISTER_RATE_LIMITS_UNDOCUMENTED",))

    def public_inspection(self, document_number: str) -> Fetched:
        if not re.fullmatch(r"\d{4}-\d{5}", document_number or ""):
            return Fetched(reason="DOCUMENT_NUMBER_INVALID")
        url = fr_public_inspection_url(document_number)
        response, received, why = self._get(url, "FR_JSON")
        if why != "OK":
            return Fetched(reason=why)
        parsed = parse_fr_public_inspection(response.body, requested=document_number, source_url=url, retrieved_at=received)
        return Fetched(reason=parsed) if isinstance(parsed, str) else Fetched(record=parsed)

    def docket_listing(self, file_number: str, *, max_pages: int = 5) -> Fetched:
        """Complete only if every result was returned and no further page exists (per_page=100)."""
        file_number = canonical_file_number(file_number or "")
        if file_number is None:
            return Fetched(reason="FILE_NUMBER_INVALID")
        numbers, count, pages, more, digests, received = [], 0, 0, True, [], None
        while more and pages < max_pages:
            url = fr_docket_url(file_number, pages + 1)
            response, received_at, why = self._get(url, "FR_JSON")
            if why != "OK":
                return Fetched(reason=why)
            parsed = parse_fr_docket_page(response.body)
            if isinstance(parsed, str):
                return Fetched(reason=parsed)
            count, page_numbers, more = parsed
            numbers.extend(page_numbers)
            digests.append(sha256_hex(response.body))
            pages += 1
            received = received_at
        complete = count == len(numbers) and not more
        listing = DocketListing(file_number=file_number, query_url=fr_docket_url(file_number), count=count,
                                returned=len(numbers), pages_fetched=pages, complete=complete,
                                document_numbers=tuple(numbers), retrieved_at=received,
                                payload_digest=sha256_hex("".join(digests)))
        limits = ("FEDERAL_REGISTER_RATE_LIMITS_UNDOCUMENTED",) + (() if complete else ("RESULT_SET_INCOMPLETE",))
        return Fetched(record=listing, limitations=limits)
