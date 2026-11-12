"""C15 Phase 1 Slice 3: structural identities, contract v3.4 §19.

These keys describe supplied projections only. They do not verify source mappings,
provenance, metric windows, economic equality or independence. C15 remains OPEN.
"""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BeforeValidator, ConfigDict, Field, validate_call

from traid.fusion.models import Basis, Coverage, FusionModel, MetricObservation, Text, UtcDatetime
from traid.fusion.serialization import id_digest


class _IdentityModel(FusionModel):
    model_config = ConfigDict(strict=True, revalidate_instances="always")


class SeriesKey(_IdentityModel):
    """All six fields are required, including explicit nulls; no source inference."""

    kind: Text
    section: Text
    symbol: Text | None
    interval: Text | None
    source: Text | None
    qualifier: Text | None


class SlotInstant(_IdentityModel):
    form: Literal["INSTANT"]
    at: UtcDatetime


class SlotWindow(_IdentityModel):
    form: Literal["WINDOW_SESSION"]
    window_start: UtcDatetime
    session_start: UtcDatetime


class SlotPeriod(_IdentityModel):
    form: Literal["REFERENCE_PERIOD"]
    period: Text


class SlotClaim(_IdentityModel):
    form: Literal["CLAIM_ID"]
    claim_id: Annotated[Text, Field(pattern=r"^[0-9a-f]{64}$")]


class Slot(_IdentityModel):
    series_key: SeriesKey
    slot_time: Annotated[SlotInstant | SlotWindow | SlotPeriod | SlotClaim, Field(discriminator="form")]


def _series_projection(key: SeriesKey) -> dict:
    return {"kind": key.kind, "section": key.section, "symbol": key.symbol,
            "interval": key.interval, "source": key.source, "qualifier": key.qualifier}


def _slot_projection(slot: Slot) -> dict:
    time = slot.slot_time
    if isinstance(time, SlotInstant):
        value = {"form": "INSTANT", "at": time.at}
    elif isinstance(time, SlotWindow):
        value = {"form": "WINDOW_SESSION", "window_start": time.window_start,
                 "session_start": time.session_start}
    elif isinstance(time, SlotPeriod):
        value = {"form": "REFERENCE_PERIOD", "period": time.period}
    else:
        value = {"form": "CLAIM_ID", "claim_id": time.claim_id}
    return {"series_key": _series_projection(slot.series_key), "slot_time": value}


def _metric_projection(metric: MetricObservation) -> dict:
    # Revalidate even caller-created model_construct/model_copy instances before hashing.
    metric = MetricObservation.model_validate(
        {"name": metric.name, "state": metric.state, "value": metric.value,
         "unit": metric.unit, "window_id": metric.window_id, "reason": metric.reason}, strict=True,
    )
    return {"name": metric.name, "state": metric.state.value, "value": metric.value,
            "unit": metric.unit, "window_id": metric.window_id, "reason": metric.reason}


def _ordered_metrics(metrics: tuple[MetricObservation, ...]) -> tuple[MetricObservation, ...]:
    if type(metrics) is not tuple or any(type(metric) is not MetricObservation for metric in metrics):
        raise ValueError("metrics must be a tuple of MetricObservation instances")
    previous = None
    for metric in metrics:
        _metric_projection(metric)
        key = (metric.name, metric.window_id is not None, metric.window_id or "")
        if previous is not None and key <= previous:
            raise ValueError("metrics must have unique (name, window_id) keys in ascending order")
        previous = key
    return metrics


@validate_call(config=ConfigDict(strict=True))
def series_id(series_key: SeriesKey) -> str:
    """Hash the six-field key; association only, never proof of shared inputs."""
    return "sr1:" + id_digest("c15.series.v1", _series_projection(series_key))


@validate_call(config=ConfigDict(strict=True))
def slot_id(slot: Slot) -> str:
    """Hash the full key and tagged slot, without source-specific interpretation."""
    return "sl1:" + id_digest("c15.slot.v1", _slot_projection(slot))


@validate_call(config=ConfigDict(strict=True))
def exposed_content_id(
    *, slot: Slot, coverage: Coverage,
    metrics: Annotated[tuple[MetricObservation, ...], BeforeValidator(_ordered_metrics)], basis: Basis,
) -> str:
    """Hash the exposed projection only; no delivery or assessment content."""
    coverage = Coverage.model_validate(
        {"earliest_time": coverage.earliest_time, "latest_time": coverage.latest_time,
         "contributing_count": coverage.contributing_count, "interval": coverage.interval}, strict=True,
    )
    value = {
        "slot": slot_id(slot),
        "coverage": {"earliest_time": coverage.earliest_time, "latest_time": coverage.latest_time,
                     "contributing_count": coverage.contributing_count, "interval": coverage.interval},
        "metrics": tuple(_metric_projection(metric) for metric in metrics),
        "basis": basis.value,
    }
    return "xc1:" + id_digest("c15.xc.v1", value)
