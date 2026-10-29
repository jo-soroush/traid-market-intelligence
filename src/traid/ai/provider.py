"""Provider-neutral AI boundary. Core C14 code depends only on this module, never on a model family.

A provider performs one SETUP (for example resolving credentials) and at most one HTTP exchange per
``send``. It never raises: every failure is a ``ProviderFailure`` with a reason code and an explicit
``retry_safe`` decision, so retry policy stays in provider-neutral code and an unknown remote outcome
is never retried. Model output is returned as a neutral ``ModelReply``; it is untrusted data.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Protocol


@dataclass(frozen=True)
class ProviderDescription:
    provider: str
    api: str
    model_id: str
    source_region: str | None
    approved_destination_regions: tuple[str, ...]
    destinations_verified_on: date | None


@dataclass(frozen=True)
class ProviderRequest:
    system_prompt: str
    user_text: str                       # the canonical JSON of the AIInterpretationRequest
    tool_name: str
    tool_description: str
    tool_schema: dict
    max_tokens: int
    temperature: float


@dataclass(frozen=True)
class ContentBlock:
    kind: str                            # "text", "tool_use" or "other"
    text: str | None = None
    tool_name: str | None = None
    tool_use_id: str | None = None
    tool_input: Any = None
    other_type: str | None = None


@dataclass(frozen=True)
class ModelReply:
    stop_reason: str | None
    role: str | None
    blocks: tuple[ContentBlock, ...]
    raw_text: str                        # canonical serialization of the provider response
    raw_size: int
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    provider_latency_ms: int | None = None
    request_id: str | None = None
    http_sends: int = 1


@dataclass(frozen=True)
class ProviderFailure:
    code: str                            # an AI_UNAVAILABLE reason code
    retry_safe: bool
    http_sends: int
    detail: str = ""
    request_id: str | None = None


@dataclass
class ProviderSession:
    """Whatever SETUP produced (for example frozen credentials); opaque to core code."""
    state: Any = None
    sends: int = 0
    extra: dict = field(default_factory=dict)


class AIProvider(Protocol):
    def describe(self) -> ProviderDescription: ...

    def setup(self) -> ProviderSession | ProviderFailure: ...

    def send(self, session: ProviderSession, request: ProviderRequest, attempt: int, connect_timeout: float,
             read_timeout: float) -> ModelReply | ProviderFailure: ...
