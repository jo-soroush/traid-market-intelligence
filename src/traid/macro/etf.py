"""C12 ETF institutional/market data foundation: applicability, providers, observations, coverage.

No ETF numeric provider is approved (C12 ETF provider review, 2026-10-21): Farside
rejects automated access with a bot challenge; SoSoValue's documented API needs an
approved key, has undocumented flow methodology and only a 1-month history; Glassnode
is paid and its flows are holdings-change estimates; BlackRock's website terms forbid
automated copying. So every observation from a provider that is not APPROVED is
excluded and no ETF number is ever reported.

The asset-to-fund mapping records fund identity verified against SEC EDGAR
(company_tickers_exchange.json: CIK, registrant name, ticker, exchange). That a fund
holds spot BTC is a curated assertion with its evidence, not an SEC classification.

A mapping is itself knowledge with a time: it is usable only at evaluation times at or
after ``available_at`` (when TraID obtained it), and a later mapping version never
rewrites an earlier evaluation. It describes the fund set as of ``identity_retrieved_on``.
A fund's validity period is recorded only with evidence; when it is unknown (no verified
launch or listing date), the fund is applicable from the mapping's as-of date onward and
coverage for any earlier trade date is unavailable, never retroactively populated.
US-listed ETF trade dates are US exchange session dates, compared in America/New_York.

Metric identities are strict: net flow, net assets, trading volume, traded value,
shares outstanding and BTC holdings are different facts. No metric is derived from
another here (volume and AUM change are never flows), and an aggregate exists only
when every applicable fund has an observation of the same metric, basis and trade date
from one approved provider. Missing data is an explicit gap, never zero.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation, localcontext
from enum import StrEnum
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import Field, model_validator

from traid.domain.models import SourceProvenance
from traid.liquidity import Metric
from traid.macro.models import CANONICAL, MacroModel, digest, rank, utc

ENGINE_VERSION = "c12-etf-evidence-2"
MAX_OBSERVATIONS = 100000
MAX_MAPPINGS = 1000
NEW_YORK = ZoneInfo("America/New_York")


class Applicability(StrEnum):
    CURATED_SPOT_BTC = "CURATED_SPOT_BTC"    # curator-asserted spot BTC fund, identity verified on EDGAR
    UNVERIFIED = "UNVERIFIED"                # identity verified, spot-BTC applicability not yet established


class EtfFund(MacroModel):
    ticker: str = Field(pattern=r"^[A-Z]{1,5}$")
    registrant_name: str = Field(min_length=1)
    cik: int = Field(gt=0)
    exchange: str = Field(min_length=1)
    applicability: Applicability
    applicability_evidence: str = Field(min_length=1)
    valid_from: date | None = None           # first trade date the applicability holds, only with evidence
    valid_until: date | None = None          # last such trade date, only with evidence
    validity_evidence: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validity_is_evidenced(self):
        if (self.valid_from is None and self.valid_until is None) != (self.validity_evidence is None):
            raise ValueError("a validity period requires its evidence, and evidence requires a period")
        if self.valid_from is not None and self.valid_until is not None and self.valid_until < self.valid_from:
            raise ValueError("validity period must be ordered")
        return self

    def valid_on(self, day: date, as_of: date) -> bool | None:
        """Applicable on ``day``: True/False when known, None when its validity there is unverified."""
        if self.valid_until is not None and day > self.valid_until:
            return False
        if self.valid_from is not None:
            return day >= self.valid_from
        return True if day >= as_of else None


class AssetEtfMapping(MacroModel):
    asset: Literal["BTC"]
    jurisdiction: Literal["US"]
    mapping_version: str = Field(pattern=r"^[A-Za-z0-9._-]+$")
    funds: tuple[EtfFund, ...] = Field(min_length=1)
    identity_source: str = Field(min_length=1)
    identity_retrieved_on: date                 # the mapping describes the fund set as of this date
    available_at: datetime                      # when TraID obtained the mapping; unusable before
    available_at_evidence: str = Field(min_length=1)
    limitations: tuple[str, ...] = (
        "MAPPED_FUNDS_ONLY_COMPLETENESS_OF_THE_US_SPOT_BTC_ETF_SET_NOT_PROVEN",
        "SPOT_BTC_APPLICABILITY_IS_A_CURATED_ASSERTION",
        "FUND_VALIDITY_BEFORE_THE_MAPPING_DATE_UNVERIFIED_UNLESS_RECORDED",
    )

    @model_validator(mode="after")
    def ordered(self):
        tickers = [f.ticker for f in self.funds]
        if tickers != sorted(set(tickers)) or len({f.cik for f in self.funds}) != len(self.funds):
            raise ValueError("funds must be unique by ticker and CIK, ordered by ticker")
        if self.available_at.date() < self.identity_retrieved_on:
            raise ValueError("a mapping cannot be available before the facts it records were retrieved")
        return self

    def applicable(self) -> tuple[EtfFund, ...]:
        return tuple(f for f in self.funds if f.applicability is Applicability.CURATED_SPOT_BTC)


_GLASSNODE = "Glassnode US Spot ETF metric documentation lists this fund as a US spot Bitcoin ETF (third-party)"
US_SPOT_BTC_ETFS = AssetEtfMapping(
    asset="BTC", jurisdiction="US", mapping_version="us-spot-btc-2026-10-21",
    identity_source="https://www.sec.gov/files/company_tickers_exchange.json", identity_retrieved_on=date(2026, 10, 21),
    # Conservative knowledge time: the commit that first recorded this mapping in TraID.
    available_at=datetime.fromisoformat("2026-10-21T21:58:30+02:00"),
    available_at_evidence="First recorded in TraID commit 7a76e30 (author date 2026-10-21T21:58:30+02:00)",
    funds=tuple(sorted((
        EtfFund(ticker="ARKB", registrant_name="Ark 21Shares Bitcoin ETF", cik=1869699, exchange="CBOE",
                applicability=Applicability.CURATED_SPOT_BTC, applicability_evidence=_GLASSNODE),
        EtfFund(ticker="BITB", registrant_name="Bitwise Bitcoin ETF", cik=1763415, exchange="NYSE",
                applicability=Applicability.CURATED_SPOT_BTC, applicability_evidence=_GLASSNODE),
        EtfFund(ticker="BRRR", registrant_name="CoinShares Bitcoin ETF", cik=1841175, exchange="Nasdaq",
                applicability=Applicability.CURATED_SPOT_BTC, applicability_evidence=_GLASSNODE),
        EtfFund(ticker="BTC", registrant_name="Grayscale Bitcoin Mini Trust ETF", cik=2015034, exchange="NYSE",
                applicability=Applicability.CURATED_SPOT_BTC, applicability_evidence=_GLASSNODE),
        EtfFund(ticker="BTCO", registrant_name="Invesco Galaxy Bitcoin ETF", cik=1855781, exchange="CBOE",
                applicability=Applicability.CURATED_SPOT_BTC, applicability_evidence=_GLASSNODE),
        EtfFund(ticker="BTCW", registrant_name="WisdomTree Bitcoin Fund", cik=1850391, exchange="CBOE",
                applicability=Applicability.CURATED_SPOT_BTC, applicability_evidence=_GLASSNODE),
        EtfFund(ticker="EZBC", registrant_name="Franklin Templeton Digital Holdings Trust", cik=1992870, exchange="CBOE",
                applicability=Applicability.CURATED_SPOT_BTC, applicability_evidence=_GLASSNODE),
        EtfFund(ticker="FBTC", registrant_name="Fidelity Wise Origin Bitcoin Fund", cik=1852317, exchange="CBOE",
                applicability=Applicability.CURATED_SPOT_BTC, applicability_evidence=_GLASSNODE),
        EtfFund(ticker="GBTC", registrant_name="Grayscale Bitcoin Trust ETF", cik=1588489, exchange="NYSE",
                applicability=Applicability.CURATED_SPOT_BTC, applicability_evidence=_GLASSNODE),
        EtfFund(ticker="HODL", registrant_name="VanEck Bitcoin ETF", cik=1838028, exchange="CBOE",
                applicability=Applicability.CURATED_SPOT_BTC, applicability_evidence=_GLASSNODE),
        EtfFund(ticker="IBIT", registrant_name="iShares Bitcoin Trust ETF", cik=1980994, exchange="Nasdaq",
                applicability=Applicability.CURATED_SPOT_BTC, applicability_evidence=_GLASSNODE),
        EtfFund(ticker="MSBT", registrant_name="Morgan Stanley Bitcoin Trust", cik=2103612, exchange="NYSE",
                applicability=Applicability.UNVERIFIED,
                applicability_evidence="Listed on EDGAR; spot-BTC fund status not established by a verified source"),
    ), key=lambda f: f.ticker)))


def verify_mapping_identity(mapping: AssetEtfMapping, company_tickers_exchange: dict) -> tuple[str, ...]:
    """Problems found comparing each fund to SEC's official ticker file (empty: identities match)."""
    fields = company_tickers_exchange.get("fields")
    rows = company_tickers_exchange.get("data")
    if fields != ["cik", "name", "ticker", "exchange"] or not isinstance(rows, list):
        return ("SEC_TICKER_FILE_SHAPE_UNEXPECTED",)
    by_ticker: dict[str, list[dict]] = {}
    for row in rows:
        record = dict(zip(fields, row))
        by_ticker.setdefault(record["ticker"], []).append(record)
    problems = []
    for fund in mapping.funds:
        hits = by_ticker.get(fund.ticker, [])
        if len(hits) != 1:
            problems.append(f"{fund.ticker}:NOT_UNIQUELY_LISTED")
        elif (hits[0]["cik"], hits[0]["name"], hits[0]["exchange"]) != (fund.cik, fund.registrant_name, fund.exchange):
            problems.append(f"{fund.ticker}:IDENTITY_MISMATCH")
    return tuple(problems)


# ------------------------------------------------------------------------- providers
class ProviderState(StrEnum):
    APPROVED = "APPROVED"
    UNVERIFIED = "UNVERIFIED"
    NOT_SUITABLE = "NOT_SUITABLE"


class EtfProvider(MacroModel):
    provider_id: str = Field(pattern=r"^[a-z0-9_]+$")
    name: str
    state: ProviderState
    reason: str
    documentation_url: str
    approval_reference: str | None = None   # the owner's recorded approval; required to be APPROVED

    @model_validator(mode="after")
    def approval_is_explicit(self):
        if (self.state is ProviderState.APPROVED) != bool(self.approval_reference):
            raise ValueError("a provider is APPROVED exactly when an approval reference is recorded")
        return self


PROVIDERS = (
    EtfProvider(provider_id="farside", name="Farside Investors", state=ProviderState.NOT_SUITABLE,
                reason="AUTOMATED_ACCESS_REJECTED_BY_BOT_CHALLENGE_TERMS_UNVERIFIED",
                documentation_url="https://farside.co.uk/btc/"),
    EtfProvider(provider_id="sosovalue", name="SoSoValue", state=ProviderState.UNVERIFIED,
                reason="API_KEY_APPROVAL_PRICING_TERMS_AND_FLOW_METHOD_UNVERIFIED_ONE_MONTH_HISTORY",
                documentation_url="https://sosovalue.gitbook.io/soso-value-api-doc"),
    EtfProvider(provider_id="glassnode", name="Glassnode", state=ProviderState.UNVERIFIED,
                reason="PAID_ENTITLEMENT_UNVERIFIED_FLOWS_ARE_HOLDINGS_CHANGE_ESTIMATES",
                documentation_url="https://docs.glassnode.com/basic-api/endpoints/institutions"),
    EtfProvider(provider_id="ishares_website", name="BlackRock iShares website", state=ProviderState.NOT_SUITABLE,
                reason="WEBSITE_TERMS_PROHIBIT_AUTOMATED_MONITORING_OR_COPYING",
                documentation_url="https://www.blackrock.com/corporate/compliance/terms-and-conditions"),
)


# ---------------------------------------------------------------------- observations
class EtfMetric(StrEnum):
    NET_FLOW_USD = "NET_FLOW_USD"
    NET_ASSETS_USD = "NET_ASSETS_USD"
    TRADING_VOLUME_SHARES = "TRADING_VOLUME_SHARES"
    TRADED_VALUE_USD = "TRADED_VALUE_USD"
    SHARES_OUTSTANDING = "SHARES_OUTSTANDING"
    BTC_HOLDINGS = "BTC_HOLDINGS"


UNITS = {EtfMetric.NET_FLOW_USD: "USD", EtfMetric.NET_ASSETS_USD: "USD", EtfMetric.TRADING_VOLUME_SHARES: "shares",
         EtfMetric.TRADED_VALUE_USD: "USD", EtfMetric.SHARES_OUTSTANDING: "shares", EtfMetric.BTC_HOLDINGS: "BTC"}


class ValueBasis(StrEnum):
    REPORTED = "REPORTED"                    # the fund or provider reports the figure itself
    PROVIDER_ESTIMATE = "PROVIDER_ESTIMATE"  # the provider computes it (e.g. holdings change x price)
    TRAID_DERIVED = "TRAID_DERIVED"          # computed by TraID; none is implemented in C12


class EtfObservation(MacroModel):
    provider_id: str
    ticker: str
    metric: EtfMetric
    trade_date: date
    raw_value: str | None                    # exactly as the provider published it; None = provider null
    value: Decimal | None
    unit: str
    basis: ValueBasis
    methodology: str = Field(min_length=1)
    as_of: datetime | None
    published_at: datetime | None
    provenance: SourceProvenance

    @model_validator(mode="after")
    def faithful(self):
        if self.unit != UNITS[self.metric]:
            raise ValueError("unit must be the metric's unit")
        if self.raw_value is None:
            if self.value is not None:
                raise ValueError("a provider null cannot carry a value")
        else:
            try:
                parsed = Decimal(self.raw_value.strip())
            except InvalidOperation as error:
                raise ValueError("raw value must be a decimal") from error
            if self.value is None or parsed != self.value or not parsed.is_finite():
                raise ValueError("value must be the exact decimal of the raw value")
        if self.basis is ValueBasis.TRAID_DERIVED:
            raise ValueError("no TraID-derived ETF metric is approved in C12")
        if self.published_at is not None and self.provenance.received_timestamp < self.published_at:
            raise ValueError("an observation cannot be received before its publication")
        return self


# -------------------------------------------------------------------------- evidence
class FundStatus(StrEnum):
    OBSERVED = "OBSERVED"
    PROVIDER_NULL = "PROVIDER_NULL"
    MISSING = "MISSING"
    CONFLICT = "CONFLICT"
    NO_APPROVED_PROVIDER = "NO_APPROVED_PROVIDER"


class FundMetric(MacroModel):
    ticker: str
    status: FundStatus
    value: Metric
    trade_date: date | None
    basis: ValueBasis | None
    observation: EtfObservation | None


class MetricCoverage(MacroModel):
    metric: EtfMetric
    trade_date: date | None
    funds: tuple[FundMetric, ...]
    aggregate: Metric
    coverage: Literal["COMPLETE", "PARTIAL", "NONE"]
    reasons: tuple[str, ...]


class EtfEvidenceReport(MacroModel):
    engine_version: str = ENGINE_VERSION
    evaluation_time: datetime
    asset: Literal["BTC"]
    mapping_state: Literal["AVAILABLE", "NO_MAPPING_KNOWN_AT_EVALUATION_TIME", "CONFLICTING_MAPPING_VERSIONS"]
    mapping_version: str | None
    mapping_digest: str | None
    mapping_as_of: date | None
    mapping_available_at: datetime | None
    excluded_mappings_after_evaluation: int = Field(ge=0)
    provider: EtfProvider | None
    provider_state: Literal["APPROVED", "NO_APPROVED_PROVIDER"]
    metrics: tuple[MetricCoverage, ...]
    unverified_applicability: tuple[str, ...]
    excluded_after_evaluation: int = Field(ge=0)
    excluded_unapproved: int = Field(ge=0)
    providers: tuple[EtfProvider, ...]
    limitations: tuple[str, ...] = (
        "NO_ETF_NUMERIC_PROVIDER_APPROVED_IN_C12",
        "MISSING_ETF_DATA_IS_A_GAP_NOT_ZERO_OR_NEUTRAL",
        "VOLUME_AND_AUM_CHANGES_ARE_NOT_FLOWS",
        "COVERAGE_IS_THE_MAPPED_FUND_SET_ONLY",
        "NOT_A_TRADE_SIGNAL_OR_AUTHORIZATION",
    )

    @model_validator(mode="after")
    def no_numbers_without_approval(self):
        if self.provider_state == "NO_APPROVED_PROVIDER" and any(
                m.aggregate.value is not None or any(f.value.value is not None for f in m.funds) for m in self.metrics):
            raise ValueError("no ETF number may appear without an approved provider")
        return self


def _mapping_at(mappings: tuple[AssetEtfMapping, ...], T: datetime):
    """The latest mapping TraID had obtained by T; later versions are counted, never read."""
    known, later = [], 0
    for m in mappings:
        if type(m) is not AssetEtfMapping:
            raise ValueError("AssetEtfMapping required")
        if utc(m.available_at) > T:
            later += 1
            continue
        known.append(AssetEtfMapping.model_validate(m.model_dump()))
    if not known:
        return None, "NO_MAPPING_KNOWN_AT_EVALUATION_TIME", later
    newest = max(m.available_at for m in known)
    latest = {digest(m): m for m in known if m.available_at == newest}
    if len(latest) > 1:
        return None, "CONFLICTING_MAPPING_VERSIONS", later
    return next(iter(latest.values())), "AVAILABLE", later


def build_etf_evidence(
    *, evaluation_time: datetime, mappings: tuple[AssetEtfMapping, ...] = (US_SPOT_BTC_ETFS,),
    providers: tuple[EtfProvider, ...] = PROVIDERS, observations: tuple[EtfObservation, ...] = (),
    trade_date: date | None = None,
) -> EtfEvidenceReport:
    """Per-fund and aggregate ETF coverage at T for one approved provider (or none)."""
    if not isinstance(mappings, tuple) or not isinstance(providers, tuple) or not isinstance(observations, tuple):
        raise ValueError("tuples of mappings, providers and observations required")
    if len(observations) > MAX_OBSERVATIONS or len(mappings) > MAX_MAPPINGS:
        raise ValueError("too many observations or mappings")
    T = utc(evaluation_time, "evaluation_time")
    session = T.astimezone(NEW_YORK).date()     # the latest US exchange session date that can have begun by T
    if trade_date is not None and trade_date > session:
        raise ValueError("trade_date is after the evaluation time's US session date")
    mapping, mapping_state, later_mappings = _mapping_at(mappings, T)
    providers = tuple(EtfProvider.model_validate(p.model_dump()) for p in providers)
    approved = [p for p in providers if p.state is ProviderState.APPROVED]
    if len(approved) > 1:
        raise ValueError("at most one approved ETF provider may supply one evidence report")
    provider = approved[0] if approved else None
    known, later, unapproved = [], 0, 0
    for o in observations:
        if type(o) is not EtfObservation or type(o.provenance) is not SourceProvenance:
            raise ValueError("EtfObservation required")
        if o.provenance.received_timestamp > T or any(t is not None and utc(t) > T for t in (o.published_at, o.as_of)) \
                or o.trade_date > session:
            later += 1
            continue
        o = EtfObservation.model_validate(o.model_dump())
        if provider is None or o.provider_id != provider.provider_id:
            unapproved += 1
            continue
        if mapping is not None and mapping_fund(mapping, o.ticker) is None:
            raise ValueError("ETF_TICKER_NOT_IN_MAPPING")
        known.append(o)
    metrics = tuple(_metric(metric, mapping, mapping_state, known, provider, trade_date, session) for metric in EtfMetric)
    return EtfEvidenceReport(
        evaluation_time=T, asset="BTC", mapping_state=mapping_state,
        mapping_version=mapping.mapping_version if mapping else None, mapping_digest=digest(mapping) if mapping else None,
        mapping_as_of=mapping.identity_retrieved_on if mapping else None,
        mapping_available_at=mapping.available_at if mapping else None, excluded_mappings_after_evaluation=later_mappings,
        provider=provider, provider_state="APPROVED" if provider else "NO_APPROVED_PROVIDER", metrics=metrics,
        unverified_applicability=tuple(f.ticker for f in (mapping.funds if mapping else ())
                                       if f.applicability is not Applicability.CURATED_SPOT_BTC),
        excluded_after_evaluation=later, excluded_unapproved=unapproved, providers=providers)


def mapping_fund(mapping: AssetEtfMapping, ticker: str) -> EtfFund | None:
    return next((f for f in mapping.funds if f.ticker == ticker), None)


def _funds_on(mapping: AssetEtfMapping, day: date):
    """Applicable funds on a trade date, or None when the mapping cannot say for that date."""
    states = {f.ticker: f.valid_on(day, mapping.identity_retrieved_on) for f in mapping.applicable()}
    if None in states.values():
        return None
    return tuple(f for f in mapping.applicable() if states[f.ticker])


def _metric(metric: EtfMetric, mapping, mapping_state, known, provider, trade_date, session) -> MetricCoverage:
    unit = UNITS[metric]
    rows = [o for o in known if o.metric is metric] if provider is not None else []
    date_ = trade_date or (max(o.trade_date for o in rows) if rows else None)
    if mapping is None:
        why = mapping_state
    else:
        funds = _funds_on(mapping, date_ or session)
        why = "FUND_VALIDITY_AT_TRADE_DATE_UNVERIFIED" if funds is None else (
            "NO_MAPPED_FUND_VALID_AT_TRADE_DATE" if not funds else None)
    if why is not None:
        return MetricCoverage(metric=metric, trade_date=date_, coverage="NONE", aggregate=_na(unit, why),
                              reasons=(why,), funds=())
    if provider is None:
        why = "NO_APPROVED_ETF_PROVIDER"
        return MetricCoverage(metric=metric, trade_date=trade_date, coverage="NONE", aggregate=_na(unit, why),
                              reasons=(why,), funds=tuple(FundMetric(ticker=f.ticker, status=FundStatus.NO_APPROVED_PROVIDER,
                                                                      value=_na(unit, why), trade_date=None, basis=None,
                                                                      observation=None) for f in funds))
    out, reasons = [], []
    for fund in funds:
        group = [o for o in rows if o.ticker == fund.ticker and o.trade_date == date_]
        if not group:
            out.append(FundMetric(ticker=fund.ticker, status=FundStatus.MISSING, value=_na(unit, "NOT_OBSERVED"),
                                  trade_date=date_, basis=None, observation=None))
            continue
        # Latest receipt is what TraID knew; equal values in other spellings collapse deterministically.
        newest = max(o.provenance.received_timestamp for o in group)
        latest = [o for o in group if o.provenance.received_timestamp == newest]
        if len({(o.value, o.raw_value is None, o.basis) for o in latest}) > 1:
            out.append(FundMetric(ticker=fund.ticker, status=FundStatus.CONFLICT, value=_na(unit, "CONFLICTING_OBSERVATIONS"),
                                  trade_date=date_, basis=None, observation=None))
            continue
        o = min(latest, key=rank)
        if o.value is None:
            out.append(FundMetric(ticker=fund.ticker, status=FundStatus.PROVIDER_NULL, value=_na(unit, "PROVIDER_PUBLISHED_NULL"),
                                  trade_date=date_, basis=o.basis, observation=o))
        else:
            out.append(FundMetric(ticker=fund.ticker, status=FundStatus.OBSERVED, value=Metric(value=o.value, unit=unit),
                                  trade_date=date_, basis=o.basis, observation=o))
    observed = [f for f in out if f.status is FundStatus.OBSERVED]
    bases = {f.basis for f in observed}
    if observed and len(observed) == len(out) and len(bases) == 1:
        total = _exact_sum(f.value.value for f in observed)
        aggregate, coverage = Metric(value=total, unit=unit), "COMPLETE"
    else:
        missing = [f.ticker for f in out if f.status is not FundStatus.OBSERVED]
        if missing:
            reasons.append("INCOMPLETE_FUND_COVERAGE:" + ",".join(missing))
        if len(bases) > 1:
            reasons.append("MIXED_VALUE_BASIS")
        aggregate = _na(unit, reasons[0] if reasons else "NO_OBSERVATIONS")
        coverage = "PARTIAL" if observed else "NONE"
    return MetricCoverage(metric=metric, trade_date=date_, funds=tuple(out), aggregate=aggregate, coverage=coverage,
                          reasons=tuple(reasons))


def _exact_sum(values) -> Decimal:
    with localcontext(CANONICAL):
        return sum(values, Decimal(0))


def _na(unit: str, reason: str) -> Metric:
    return Metric(value=None, unit=unit, reason=reason)
