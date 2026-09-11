"""Structured semantic Card-alignment checks for the C01 Harness."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


C01 = "V1-C01"

_C01_DOMAINS = {
    "baseline": ("repository baseline", "reproducible repository", "package baseline"),
    "configuration": ("deterministic configuration", "configuration loading", "config"),
    "health": ("health endpoint", "application health", "app boot"),
    "tests": ("pytest discovery", "baseline tests", "test discovery", "validation"),
    "harness": ("engineering harness", "content alignment", "scope protection", "card gate"),
    "security": ("secret scan", "credential scan", "security baseline", "no secrets"),
    "delivery": ("docker baseline", "ci skeleton", "continuous integration"),
}

_FUTURE_DOMAINS = {
    "V1-C02": ("canonical domain model", "provider-neutral domain model", "typed market model"),
    "V1-C03": ("exchange adapter", "adapter contract", "capability discovery"),
    "V1-C04": ("hyperliquid adapter", "live btc data", "websocket market data"),
    "V1-C16": ("strategy engine", "trade candidate", "signal fusion"),
    "V1-C17": ("risk gate", "position sizing", "leverage"),
    "V1-C18": ("backtest engine", "historical replay", "anti-lookahead"),
}

_OUT_OF_SCOPE = (
    "market data ingestion",
    "order book analytics",
    "trade flow",
    "macro intelligence",
    "news verification",
    "bedrock integration",
    "live trading",
    "order placement",
    "wallet private key",
    "redis",
    "kafka",
    "kubernetes",
    "microservices",
)


@dataclass(frozen=True)
class CardRequest:
    """Machine-readable request facts extracted before alignment evaluation."""

    card_id: str
    objective: str
    behaviors: tuple[str, ...] = ()
    files: tuple[str, ...] = ()
    validation: tuple[str, ...] = ()
    dependencies_complete: bool = True
    repository_state_conflict: bool = False
    invented_material_requirement: bool = False
    next_card_requested: bool = False
    current_card_complete: bool = False
    next_card_authorized: bool = False
    asks_completion: bool = False
    mandatory_validation_passed: bool = True


@dataclass(frozen=True)
class AlignmentResult:
    passed: bool
    reason_codes: tuple[str, ...] = field(default_factory=tuple)
    matched_domains: tuple[str, ...] = field(default_factory=tuple)


def _contains(text: str, phrase: str) -> bool:
    """Match semantic phrases on normalized boundaries, not exact requests."""

    normalized = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
    candidate = re.sub(r"[^a-z0-9]+", " ", phrase.lower()).strip()
    return bool(candidate) and f" {candidate} " in f" {normalized} "


def evaluate_content_alignment(request: CardRequest) -> AlignmentResult:
    """Evaluate C01 scope and governance conditions deterministically."""

    text = " ".join((request.objective, *request.behaviors, *request.files, *request.validation))
    reasons: list[str] = []
    matched = tuple(
        name for name, phrases in _C01_DOMAINS.items() if any(_contains(text, p) for p in phrases)
    )

    if request.card_id != C01:
        reasons.append("CARD_MISMATCH")
    if request.repository_state_conflict:
        reasons.append("PROJECT_STATE_CONFLICT")
    if not request.dependencies_complete:
        reasons.append("CARD_DEPENDENCY_MISMATCH")
    if request.invented_material_requirement:
        reasons.append("INVENTED_REQUIREMENT")
    if request.next_card_requested and (not request.current_card_complete or not request.next_card_authorized):
        reasons.append("NEXT_CARD_AUTHORIZATION_BLOCKED")
    if request.asks_completion and not request.mandatory_validation_passed:
        reasons.append("CARD_QUALITY_GATE_BLOCKED")

    if any(_contains(text, phrase) for phrase in _OUT_OF_SCOPE):
        reasons.append("CARD_SCOPE_MISMATCH")
    for card_id, phrases in _FUTURE_DOMAINS.items():
        if any(_contains(text, phrase) for phrase in phrases):
            reasons.append(f"FUTURE_CARD_LEAKAGE:{card_id}")

    required = {"baseline", "harness"}
    if request.card_id == C01 and not required.issubset(matched):
        reasons.append("C01_CONTENT_INCOMPLETE")

    return AlignmentResult(
        passed=not reasons,
        reason_codes=tuple(dict.fromkeys(reasons)),
        matched_domains=matched,
    )
