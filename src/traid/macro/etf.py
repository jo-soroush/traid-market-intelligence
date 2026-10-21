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

from pydantic import Field, model_validator

from traid.domain.models import SourceProvenance
from traid.liquidity import Metric
from traid.macro.models import CANONICAL, MacroModel, digest, rank, utc

ENGINE_VERSION = "c12-etf-evidence-1"
MAX_OBSERVATIONS = 100000


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


class AssetEtfMapping(MacroModel):
    asset: Literal["BTC"]
    jurisdiction: Literal["US"]
    mapping_version: str = Field(pattern=r"^[A-Za-z0-9._-]+$")
    funds: tuple[EtfFund, ...] = Field(min_length=1)
    identity_source: str = Field(min_length=1)
    identity_retrieved_on: date
    limitations: tuple[str, ...] = (
        "MAPPED_FUNDS_ONLY_COMPLETENESS_OF_THE_US_SPOT_BTC_ETF_SET_NOT_PROVEN",
        "SPOT_BTC_APPLICABILITY_IS_A_CURATED_ASSERTION",
    )

    @model_validator(mode="after")
    def ordered(self):
        tickers = [f.ticker for f in self.funds]
        if tickers != sorted(set(tickers)) or len({f.cik for f in self.funds}) != len(self.funds):
            raise ValueError("funds must be unique by ticker and CIK, ordered by ticker")
        return self

    def applicable(self) -> tuple[EtfFund, ...]:
        return tuple(f for f in self.funds if f.applicability is Applicability.CURATED_SPOT_BTC)


_GLASSNODE = "Glassnode US Spot ETF metric documentation lists this fund as a US spot Bitcoin ETF (third-party)"
US_SPOT_BTC_ETFS = AssetEtfMapping(
    asset="BTC", jurisdiction="US", mapping_version="us-spot-btc-2026-10-21",
    identity_source="https://www.sec.gov/files/company_tickers_exchange.json", identity_retrieved_on=date(2026, 10, 21),
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
    mapping_version: str
    mapping_digest: str
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


def build_etf_evidence(
    *, evaluation_time: datetime, mapping: AssetEtfMapping = US_SPOT_BTC_ETFS,
    providers: tuple[EtfProvider, ...] = PROVIDERS, observations: tuple[EtfObservation, ...] = (),
    trade_date: date | None = None,
) -> EtfEvidenceReport:
    """Per-fund and aggregate ETF coverage at T for one approved provider (or none)."""
    if type(mapping) is not AssetEtfMapping or not isinstance(providers, tuple) or not isinstance(observations, tuple):
        raise ValueError("AssetEtfMapping and tuples of providers and observations required")
    if len(observations) > MAX_OBSERVATIONS:
        raise ValueError("too many observations")
    T = utc(evaluation_time, "evaluation_time")
    mapping = AssetEtfMapping.model_validate(mapping.model_dump())
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
                or o.trade_date > T.date():
            later += 1
            continue
        o = EtfObservation.model_validate(o.model_dump())
        if provider is None or o.provider_id != provider.provider_id:
            unapproved += 1
            continue
        if mapping_fund(mapping, o.ticker) is None:
            raise ValueError("ETF_TICKER_NOT_IN_MAPPING")
        known.append(o)
    applicable = mapping.applicable()
    metrics = tuple(_metric(metric, applicable, known, provider, trade_date) for metric in EtfMetric)
    return EtfEvidenceReport(
        evaluation_time=T, asset=mapping.asset, mapping_version=mapping.mapping_version, mapping_digest=digest(mapping),
        provider=provider, provider_state="APPROVED" if provider else "NO_APPROVED_PROVIDER", metrics=metrics,
        unverified_applicability=tuple(f.ticker for f in mapping.funds if f.applicability is not Applicability.CURATED_SPOT_BTC),
        excluded_after_evaluation=later, excluded_unapproved=unapproved, providers=providers)


def mapping_fund(mapping: AssetEtfMapping, ticker: str) -> EtfFund | None:
    return next((f for f in mapping.funds if f.ticker == ticker), None)


def _metric(metric: EtfMetric, funds, known, provider, trade_date) -> MetricCoverage:
    unit = UNITS[metric]
    if provider is None:
        why = "NO_APPROVED_ETF_PROVIDER"
        return MetricCoverage(metric=metric, trade_date=trade_date, coverage="NONE", aggregate=_na(unit, why),
                              reasons=(why,), funds=tuple(FundMetric(ticker=f.ticker, status=FundStatus.NO_APPROVED_PROVIDER,
                                                                      value=_na(unit, why), trade_date=None, basis=None,
                                                                      observation=None) for f in funds))
    rows = [o for o in known if o.metric is metric]
    date_ = trade_date or (max(o.trade_date for o in rows) if rows else None)
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
