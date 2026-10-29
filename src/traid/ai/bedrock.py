"""Amazon Bedrock Converse adapter for Amazon Nova Pro through the EU cross-region inference profile.

This is the only C14 module that imports boto3 or botocore, and it imports them lazily, so the core
never depends on the SDK or on a model family.

* SDK retries are off: ``Config(retries={"total_max_attempts": 1, "mode": "standard"})``; an explicit
  client config takes precedence over ``AWS_MAX_ATTEMPTS``/``AWS_RETRY_MODE`` (verified offline in the
  test suite for the pinned botocore).
* A guard on ``before-send.bedrock-runtime.Converse`` counts real HTTP sends: at most one per
  application attempt and two per invocation; any extra send raises ``SdkRetryBlocked``.
* Credentials are resolved once in SETUP from the default chain and frozen; the region is explicit.
  Credentials are never logged, recorded or returned.
* Failures are classified by error code, never by HTTP status. An unknown remote outcome is never
  retried. The two retry-safe rows rest on unverified assumptions (U-R1: connect errors happen before
  delivery; U-R2: Throttling and ModelNotReady are not processed) and stay "no retry" unless the owner
  records them as verified for the pinned version (``verified_retry_assumptions``).
"""
from __future__ import annotations

from datetime import date
import json
import threading
from typing import Callable

from traid.ai.provider import (
    ContentBlock, ModelReply, ProviderDescription, ProviderFailure, ProviderRequest, ProviderSession,
)

DEFAULT_MODEL_ID = "eu.amazon.nova-pro-v1:0"          # EU inference profile of amazon.nova-pro-v1:0
EU_DESTINATIONS = ("eu-central-1", "eu-north-1", "eu-west-1", "eu-west-3")
SEND_EVENT = "before-send.bedrock-runtime.Converse"
MAX_SENDS_PER_ATTEMPT = 1
MAX_SENDS_PER_INVOCATION = 2
RETRY_ASSUMPTIONS = {"ENDPOINT_UNREACHABLE": "U-R1", "PROVIDER_THROTTLED": "U-R2", "MODEL_NOT_READY": "U-R2"}
PROVIDER_ERRORS = frozenset({"ServiceUnavailableException", "InternalServerException", "ModelTimeoutException",
                             "ModelErrorException"})


class SdkRetryBlocked(Exception):
    """Raised by the send guard when the SDK tries to send more than allowed."""


class SendGuard:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.attempt_sends = 0
        self.total_sends = 0

    def begin_attempt(self) -> None:
        with self._lock:
            self.attempt_sends = 0

    def __call__(self, request=None, **kwargs):
        with self._lock:
            if self.attempt_sends >= MAX_SENDS_PER_ATTEMPT or self.total_sends >= MAX_SENDS_PER_INVOCATION:
                raise SdkRetryBlocked("HTTP send limit reached")
            self.attempt_sends += 1
            self.total_sends += 1
        return None     # never short-circuits; the real (or test) transport sends


def _int(value) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


class BedrockConverseProvider:
    def __init__(self, *, source_region: str, model_id: str = DEFAULT_MODEL_ID,
                 approved_destination_regions: tuple[str, ...] = EU_DESTINATIONS,
                 destinations_verified_on: date | None = None,
                 verified_retry_assumptions: frozenset[str] = frozenset(),
                 credentials_resolver: Callable[[], tuple[str, str, str | None]] | None = None,
                 client_factory: Callable | None = None) -> None:
        if not isinstance(source_region, str) or not source_region:
            raise ValueError("an explicit source region is required")
        self.source_region = source_region
        self.model_id = model_id
        self.approved_destination_regions = tuple(approved_destination_regions)
        self.destinations_verified_on = destinations_verified_on
        self.verified_retry_assumptions = frozenset(verified_retry_assumptions)
        self._resolve = credentials_resolver or self._default_credentials
        self._client_factory = client_factory or self._default_client

    # -------------------------------------------------------------------- metadata
    def describe(self) -> ProviderDescription:
        return ProviderDescription(provider="aws-bedrock", api="converse", model_id=self.model_id,
                                   source_region=self.source_region,
                                   approved_destination_regions=self.approved_destination_regions,
                                   destinations_verified_on=self.destinations_verified_on)

    # ----------------------------------------------------------------------- SETUP
    def _default_credentials(self) -> tuple[str, str, str | None]:
        import boto3
        from botocore.exceptions import NoCredentialsError
        credentials = boto3.session.Session(region_name=self.source_region).get_credentials()
        if credentials is None:
            raise NoCredentialsError()
        frozen = credentials.get_frozen_credentials()
        return frozen.access_key, frozen.secret_key, frozen.token

    def setup(self) -> ProviderSession | ProviderFailure:
        try:
            import botocore.exceptions as E
        except Exception:
            return ProviderFailure(code="REQUEST_CONSTRUCTION_FAILED", retry_safe=False, http_sends=0,
                                   detail="SDK_NOT_IMPORTABLE")
        try:
            key, secret, token = self._resolve()
        except (E.NoCredentialsError, E.PartialCredentialsError, E.CredentialRetrievalError):
            return ProviderFailure(code="CREDENTIALS_UNAVAILABLE", retry_safe=False, http_sends=0)
        except Exception:
            return ProviderFailure(code="CREDENTIALS_UNAVAILABLE", retry_safe=False, http_sends=0,
                                   detail="CREDENTIAL_RESOLUTION_ERROR")
        if not key or not secret:
            return ProviderFailure(code="CREDENTIALS_UNAVAILABLE", retry_safe=False, http_sends=0)
        return ProviderSession(state=(key, secret, token), extra={"guard": SendGuard()})

    # ------------------------------------------------------------------------ SEND
    def _default_client(self, credentials, connect_timeout: float, read_timeout: float):
        import boto3
        from botocore.config import Config
        key, secret, token = credentials
        config = Config(retries={"total_max_attempts": 1, "mode": "standard"}, max_pool_connections=1,
                        connect_timeout=connect_timeout, read_timeout=read_timeout)
        return boto3.client("bedrock-runtime", region_name=self.source_region, aws_access_key_id=key,
                            aws_secret_access_key=secret, aws_session_token=token, config=config)

    def converse_params(self, request: ProviderRequest) -> dict:
        return {
            "modelId": self.model_id,
            "system": [{"text": request.system_prompt}],
            "messages": [{"role": "user", "content": [{"text": request.user_text}]}],
            "inferenceConfig": {"maxTokens": request.max_tokens, "temperature": float(request.temperature)},
            "toolConfig": {
                "tools": [{"toolSpec": {"name": request.tool_name, "description": request.tool_description,
                                        "inputSchema": {"json": request.tool_schema}}}],
                "toolChoice": {"tool": {"name": request.tool_name}},
            },
        }

    def send(self, session: ProviderSession, request: ProviderRequest, attempt: int, connect_timeout: float,
             read_timeout: float) -> ModelReply | ProviderFailure:
        guard: SendGuard = session.extra["guard"]
        guard.begin_attempt()
        try:
            client = self._client_factory(session.state, connect_timeout, read_timeout)
            client.meta.events.register_first(SEND_EVENT, guard, unique_id="traid-c14-send-guard")
            params = self.converse_params(request)
        except Exception:
            return ProviderFailure(code="REQUEST_CONSTRUCTION_FAILED", retry_safe=False, http_sends=guard.attempt_sends)
        try:
            response = client.converse(**params)
        except Exception as error:     # every failure is classified; nothing propagates
            return self.classify(error, guard.attempt_sends)
        return self.reply(response, guard.attempt_sends)

    def _retry(self, code: str) -> bool:
        return RETRY_ASSUMPTIONS.get(code) in self.verified_retry_assumptions

    def classify(self, error: BaseException, sends: int) -> ProviderFailure:
        import botocore.exceptions as E
        request_id = None
        if isinstance(error, SdkRetryBlocked):
            code = "SDK_RETRY_BLOCKED"
        elif isinstance(error, E.ParamValidationError):
            code = "REQUEST_CONSTRUCTION_FAILED"
        elif isinstance(error, (E.NoCredentialsError, E.PartialCredentialsError, E.CredentialRetrievalError)):
            code = "CREDENTIALS_UNAVAILABLE"
        elif isinstance(error, E.ConnectTimeoutError):      # checked before its parent class
            code = "ENDPOINT_UNREACHABLE"
        elif isinstance(error, E.ProxyConnectionError):
            code = "PROXY_CONNECTION_FAILED"
        elif isinstance(error, E.EndpointConnectionError) and not isinstance(error, E.SSLError):
            code = "ENDPOINT_UNREACHABLE"
        elif isinstance(error, E.ClientError):
            response = getattr(error, "response", None) or {}
            error_code = (response.get("Error") or {}).get("Code")
            request_id = (response.get("ResponseMetadata") or {}).get("RequestId")
            if error_code == "ThrottlingException":
                code = "PROVIDER_THROTTLED"
            elif error_code == "ModelNotReadyException":
                code = "MODEL_NOT_READY"
            elif error_code in PROVIDER_ERRORS:
                code = "PROVIDER_ERROR"
            else:
                code = "PROVIDER_REJECTED_REQUEST"
        else:   # SSLError, ReadTimeoutError, ConnectionClosedError, any other error during SEND
            code = "REMOTE_OUTCOME_UNKNOWN"
        return ProviderFailure(code=code, retry_safe=self._retry(code), http_sends=sends,
                               detail=type(error).__name__, request_id=request_id)

    # -------------------------------------------------------------------- RESPONSE
    def reply(self, response: dict, sends: int) -> ModelReply:
        meta = response.get("ResponseMetadata") or {}
        body = {k: v for k, v in response.items() if k != "ResponseMetadata"}
        raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
        message = (body.get("output") or {}).get("message") if isinstance(body.get("output"), dict) else None
        message = message if isinstance(message, dict) else {}
        blocks = []
        content = message.get("content")
        for b in content if isinstance(content, list) else [content]:
            if isinstance(b, dict) and list(b) == ["text"]:
                blocks.append(ContentBlock(kind="text", text=b["text"]))
            elif isinstance(b, dict) and list(b) == ["toolUse"] and isinstance(b["toolUse"], dict):
                tu = b["toolUse"]
                blocks.append(ContentBlock(kind="tool_use", tool_name=tu.get("name"), tool_use_id=tu.get("toolUseId"),
                                           tool_input=tu.get("input")))
            else:
                blocks.append(ContentBlock(kind="other",
                                           other_type=",".join(sorted(b)) if isinstance(b, dict) else type(b).__name__))
        usage = body.get("usage") if isinstance(body.get("usage"), dict) else {}
        metrics = body.get("metrics") if isinstance(body.get("metrics"), dict) else {}
        stop = body.get("stopReason")
        return ModelReply(stop_reason=stop if isinstance(stop, str) else None, role=message.get("role"),
                          blocks=tuple(blocks), raw_text=raw, raw_size=len(raw.encode()),
                          input_tokens=_int(usage.get("inputTokens")), output_tokens=_int(usage.get("outputTokens")),
                          total_tokens=_int(usage.get("totalTokens")),
                          provider_latency_ms=_int(metrics.get("latencyMs")),
                          request_id=meta.get("RequestId") if isinstance(meta.get("RequestId"), str) else None,
                          http_sends=sends)
