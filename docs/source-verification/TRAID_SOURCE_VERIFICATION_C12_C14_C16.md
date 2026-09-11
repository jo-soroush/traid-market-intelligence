# TRAID SOURCE VERIFICATION — C12, C14, C16

**Date:** 2026-09-03  
**Scope:** Final high-value unresolved source verification block  
**Cards covered:** C12 Macro Intelligence, C14 Bedrock Structured Intelligence, C16 Typed Strategy Engine  
**Status:** Source-level verification complete enough for implementation planning; runtime approval still pending where code is adapted

---

# 1. Executive Decision

This verification block resolves the three largest remaining source ambiguities.

## C12 — NEXUS

Exact public route files now verified:

```text
src/app/api/v1/macro/route.ts
src/app/api/v1/macro/route.test.ts
src/app/api/v1/calendar/route.ts
```

NEXUS remains a strong **provider/API methodology reference**, not a stack dependency.

## C14 — Quant Flow

The current branch has changed from earlier audit assumptions.

Verified current files:

```text
src/llm.py
src/strategy/perp.py
src/strategy/grid.py
src/strategy/grid_agent.py
src/engine.py
src/config.py
tests/
prompts/
```

The strongest reusable design is now very clear:

```text
LLM call
→ bounded retry
→ JSON extraction
→ decision normalization
→ validation
→ fail closed to HOLD
→ deterministic execution boundary
```

TraID should adapt the **fail-closed structured-output pattern**, not Quant Flow's trade actions.

## C16 — Keel

Exact public source areas now verified:

```text
pipeline_engine/dsl/parser.py
pipeline_engine/dsl/interpreter.py
pipeline_engine/dsl/emitter.py
pipeline_engine/dsl/catalog.py
pipeline_engine/dsl/edits.py
pipeline_engine/dsl/differ.py
pipeline_engine/base/registry.py
pipeline_engine/base/registry_types.py
pipeline_engine/base/step.py
pipeline_engine/registry_loader.py
pipeline_engine/validation_shared.py
pipeline_engine/types.py
```

Keel remains the best architecture reference for:

```text
typed composition
registry
DSL interpretation
validation
deterministic emitted representation
```

However, a single clearly exposed public source file representing the full production "compiled strategy artifact" was not established with enough certainty.

Therefore:

```text
compiler/artifact architecture → ADAPT
exact artifact file → SOURCE FILE NOT YET VERIFIED
```

No guessing.

---

# 2. C12 — NEXUS Macro Intelligence

Repository:

```text
oyi77/1ai-nexus
```

Current public repository confirms a large finance-intelligence surface and REST v1 API.

Verified API contract:

```text
GET /api/v1/macro
GET /api/v1/calendar
```

The README states v1 endpoints use:

```text
{ data, meta, error }
```

This is useful as a response-envelope pattern.

---

# 3. Exact NEXUS Files Verified

## Macro

```text
src/app/api/v1/macro/route.ts
src/app/api/v1/macro/route.test.ts
```

## Calendar

```text
src/app/api/v1/calendar/route.ts
```

Additional public route groups include:

```text
global-macro
indonesia-macro
health
status-style functionality through v1 health endpoints
```

TraID V1 does not need to adopt the entire breadth.

---

# 4. C12 — What We Take

NEXUS demonstrates a useful provider boundary for:

```text
macro data source
↓
normalization
↓
API route
↓
consistent envelope
```

And useful product concepts:

```text
FRED-backed macro
economic calendar
central-bank schedules
cross-asset macro context
health/status
```

TraID should adapt these concepts into Python/FastAPI, not reuse Next.js routes directly.

---

# 5. C12 — What TraID Builds

TraID-owned models:

```text
MacroEvent
MacroObservation
MacroSource
MacroProviderStatus
MacroCheckpoint
```

Suggested V1 `MacroEvent` fields:

```text
event_id
event_type
name
scheduled_at
released_at
actual
forecast
previous
unit
importance
source
source_url
source_timestamp
received_timestamp
freshness_state
verification_status
provenance_id
```

V1 priority:

```text
FOMC
CPI
PCE
NFP
interest-rate decisions
```

---

# 6. C12 — What We Reject

Do not import:

```text
Next.js application architecture
Redis requirement
multi-chain services
all 34 finance modules
smart-money AI scoring
news as authoritative macro verification
```

NEXUS is broader than TraID V1 needs.

---

# 7. C12 — Final Decision

```text
NEXUS macro API structure: ADAPT
NEXUS calendar structure: ADAPT
route.ts code: REFERENCE / selective translation only
TypeScript/Next.js stack: REJECT
TraID Macro provider: BUILD
TraID canonical macro models: BUILD
```

---

# 8. C14 — Quant Flow Current Source Reality

Repository:

```text
web3spreads/quant-flow
```

The current public branch differs materially from earlier source mapping.

Current `src/` exposes:

```text
data/
plugins/
strategy/
trading/
utils/
config.py
engine.py
fees.py
llm.py
```

This means prior assumptions such as:

```text
src/agent/
src/llm/
src/backtest/
```

must no longer be treated as current exact paths.

TraID source documentation should use current paths.

---

# 9. C14 — Exact LLM File

Verified:

```text
src/llm.py
```

Important public symbols:

```text
LLMError
LLMClient
LLMClient.chat(...)
extract_json(...)
_first_json_object(...)
```

---

# 10. LLMClient.chat() — Useful Pattern

The client uses:

```text
base_url
api_key
model
temperature
timeout
max_retries
```

and sends a standard chat request.

Important resilience behavior:

```text
network error
HTTP error
JSON parsing error
empty response
```

are treated as retryable failures.

Retry is bounded.

After retry exhaustion:

```text
LLMError
```

is raised.

This is a good provider-boundary pattern.

## TraID adaptation

TraID should keep:

```text
bounded retries
timeout
explicit provider error
empty-response failure
model metadata
```

But replace OpenAI-compatible HTTP details with:

```text
BedrockProvider
```

behind a generic `AIProvider`.

---

# 11. extract_json() — High-Value Pattern

Verified behavior:

```text
1. if already dict → return
2. parse ```json fenced block
3. parse entire response
4. balanced-brace scan for first JSON object
5. reject list/scalar/non-object
6. raise ValueError on failure
```

The function explicitly guarantees:

```text
dict or failure
```

It does not silently pass malformed model output downstream.

This is valuable.

## TraID improvement

TraID should go one step further:

```text
JSON object
↓
Pydantic schema validation
↓
semantic validation
↓
StructuredIntelligence
```

So `extract_json()` is a parsing inspiration, not enough by itself.

---

# 12. Exact Fail-Closed Strategy Path

Verified current file:

```text
src/strategy/perp.py
```

Key method:

```text
_decide(...)
```

Current public behavior:

```text
LLM call failure
→ HOLD

JSON parse failure
→ HOLD

invalid action
→ HOLD

missing/invalid amount or leverage
→ HOLD
```

The source explicitly documents the principle:

```text
LLM failure must never amplify into a trading action
```

This is directly relevant to TraID.

---

# 13. Important Quant Flow Improvement Found

The source comments explain a previous bad behavior:

If model output lacked valid:

```text
amount_usd
leverage
```

the old behavior could fall back toward configured maxima.

The current code changed this to:

```text
HOLD
```

That is a strong engineering lesson.

General principle:

```text
malformed high-impact field
must not be replaced by an aggressive default
```

TraID should apply the same philosophy throughout AI output handling.

---

# 14. C14 — What TraID Takes

```text
provider failure is explicit
bounded retry
structured JSON output
strict parser
invalid output fails closed
malformed required fields fail closed
LLM health tracking
raw response can be retained for audit
prompt retained for traceability
```

Useful health concepts from `src/strategy/perp.py`:

```text
_llm_failure_streak
_llm_alert_sent
_track_llm_health(...)
llm_ok
```

TraID can adapt the concept into observability.

---

# 15. C14 — What TraID Rejects

Quant Flow allows actions such as:

```text
BUY
SELL_SHORT
CLOSE
HOLD
```

and processes model-generated:

```text
confidence
amount_usd
leverage
```

TraID V1 must not do this.

TraID AI output should never be:

```text
trade action
position size authority
leverage authority
risk approval
```

Instead output:

```text
supporting_factors
contradicting_factors
uncertainty
missing_information
evidence_refs
source_refs
```

---

# 16. C14 — Bedrock Translation

TraID architecture:

```text
Evidence Bundle
↓
AIProvider
↓
BedrockProvider
↓
Claude/Nova/other supported model
↓
raw response
↓
strict structured parser
↓
schema validation
↓
semantic validation
↓
StructuredIntelligence
```

Failure:

```text
timeout
provider unavailable
malformed JSON
schema mismatch
missing required evidence refs
```

becomes:

```text
AI_UNAVAILABLE
```

or invalidated intelligence.

Deterministic market analytics remain available.

---

# 17. C14 — Final Decision

```text
src/llm.py retry/error pattern: ADAPT
extract_json(): ADAPT METHOD
src/strategy/perp.py fail-closed pattern: ADAPT STRONG
LLM health tracking: ADAPT
trade actions from LLM: REJECT
confidence as authority: REJECT
amount/leverage from LLM: REJECT
Bedrock provider: BUILD
Pydantic TraID schema: BUILD
```

---

# 18. C16 — Keel Current Public Architecture

Repository:

```text
keel-trade/keel-trade
```

License:

```text
MIT
```

Public repository describes Keel as:

```text
Agent composes
→ Strategy graph
→ compile
→ deterministic artifact
→ backtest/live engine
```

Three core ideas are explicitly stated:

```text
same artifact between backtest/live
typed composition over freeform code
agent creates; deterministic engine executes
```

These are highly aligned with TraID.

---

# 19. Exact Keel Source Areas Verified

Root:

```text
pipeline_engine/
```

Exact files/directories:

```text
pipeline_engine/base/
pipeline_engine/dsl/
pipeline_engine/backtest_config.py
pipeline_engine/component_ranking.py
pipeline_engine/constants.py
pipeline_engine/exceptions.py
pipeline_engine/registry_loader.py
pipeline_engine/types.py
pipeline_engine/validation_shared.py
```

---

# 20. Keel DSL Files Verified

```text
pipeline_engine/dsl/catalog.py
pipeline_engine/dsl/clocks.py
pipeline_engine/dsl/differ.py
pipeline_engine/dsl/edits.py
pipeline_engine/dsl/emitter.py
pipeline_engine/dsl/errors.py
pipeline_engine/dsl/interpreter.py
pipeline_engine/dsl/judgments.py
pipeline_engine/dsl/parser.py
```

These exact files eliminate most prior uncertainty about where typed composition behavior lives.

---

# 21. Keel Registry Files Verified

```text
pipeline_engine/base/registry.py
pipeline_engine/base/registry_types.py
pipeline_engine/base/step.py
pipeline_engine/registry_loader.py
```

This is particularly useful for understanding:

```text
versioned component definitions
component registry
typed step metadata
component loading
```

---

# 22. Keel — What We Take

Strong architecture ideas:

```text
Strategy Definition
↓
parse / interpret
↓
validate
↓
resolve components from registry
↓
emit deterministic representation
↓
execute outside LLM
```

TraID does not need Keel's DSL itself in V1.

But the architecture strongly informs:

```text
StrategyDefinition
StrategyRule
StrategyArtifact
StrategyValidator
StrategyRegistry
StrategyEvaluator
```

---

# 23. Why We Should Not Import Keel DSL Wholesale

`interpreter.py` and `emitter.py` are large and support a much broader composition platform.

TraID V1 needs:

```text
one BTC strategy family
small number of deterministic rules
transparent versioned artifact
```

Adding a full custom DSL would increase:

```text
implementation cost
testing burden
maintenance
debugging complexity
```

without a measurable V1 benefit.

Therefore:

```text
Keel DSL: REFERENCE / selective pattern adaptation
TraID simple typed strategy schema: BUILD
```

---

# 24. Important Unresolved Point

The public README clearly describes a:

```text
compiled deterministic strategy artifact
```

and source reveals parser/interpreter/emitter/registry machinery.

However, this verification did not establish a single exact public file/class that can confidently be called:

```text
the production compiled artifact implementation
```

Therefore:

```text
SOURCE FILE NOT YET VERIFIED
```

for direct artifact reuse.

This is not a blocker.

TraID should implement its own smaller typed artifact.

---

# 25. Proposed TraID StrategyArtifact

Conceptually:

```text
strategy_id
strategy_version
schema_version
symbol_scope
required_evidence
entry_rules
exit_rules
stop_rule
target_rule
warmup_requirements
parameter_set
regime_constraints
created_at
artifact_hash
```

The artifact must be:

```text
immutable for a run
serializable
versioned
validatable
replayable
```

---

# 26. C16 — Final Decision

```text
Keel high-level architecture: ADAPT STRONG
registry pattern: ADAPT
validation pattern: ADAPT
DSL parser: REFERENCE ONLY
interpreter: REFERENCE ONLY
emitter concept: ADAPT
full Keel dependency: REJECT
live execution integration: REJECT
TraID StrategyArtifact: BUILD
TraID StrategyValidator: BUILD
TraID StrategyEvaluator: BUILD
```

---

# 27. Revised Final Source Status

## C12

Previously:

```text
SOURCE FILE NOT YET VERIFIED
```

Now:

```text
src/app/api/v1/macro/route.ts
src/app/api/v1/macro/route.test.ts
src/app/api/v1/calendar/route.ts
```

**RESOLVED**

---

## C14

Previously mapped to older source layout.

Current exact useful source:

```text
src/llm.py
src/strategy/perp.py
prompts/
tests/
```

**RESOLVED WITH SOURCE-DRIFT CORRECTION**

---

## C16

Now verified:

```text
pipeline_engine/dsl/*
pipeline_engine/base/*
pipeline_engine/registry_loader.py
pipeline_engine/validation_shared.py
pipeline_engine/types.py
```

Compiled artifact as one exact reusable production file:

```text
SOURCE FILE NOT YET VERIFIED
```

**ENOUGH TO PROCEED WITHOUT DIRECT KEEL DEPENDENCY**

---

# 28. Final External Source Map for V1

At this point the main external source responsibilities are sufficiently clear:

```text
C04-C10
← Hyperliquid Analytics Dashboard

C11
← HyperStats methodology only

C12
← NEXUS macro/calendar patterns

C13
← TraID build

C14
← Quant Flow fail-closed AI pattern
← TraID Bedrock implementation

C15
← CryptoRadar SignalEngine methodology

C16
← Keel typed strategy architecture
← CryptoRadar detector pattern
← TraID implementation

C17
← TraID build

C18
← Hyperliquid Backtester

C19
← CryptoRadar OutcomeEvaluator/Tracker

C20-C27
← primarily TraID-owned integration/product/governance
```

---

# 29. Source Selection Is Now Sufficiently Closed

The external-research phase can now stop being open-ended.

We have enough verified source direction to begin controlled implementation.

Remaining source work should happen **just-in-time per Card**, not as another large research phase.

For any `ADAPT` Card, immediately before coding:

```text
open exact file
confirm current commit/path
confirm license
inspect exact function
write tests
adapt only required method
record provenance
```

This prevents repository drift from silently changing TraID assumptions.

---

# 30. Final Engineering Principle

The final V1 source strategy is now:

```text
EXTERNAL REPOS
→ give us proven patterns and useful algorithms

TRAID
→ owns contracts, correctness, safety, integration, and product behavior
```

The project should not continue searching for repositories merely to fill every Card.

From here, a new external technology or repository should enter only when an active Card has a measurable gap that the current source set cannot solve cleanly.
