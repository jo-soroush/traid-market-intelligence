# Traid Open Source Project Audit Rules

## Purpose

This document defines the mandatory audit standard for every open source
project evaluated for possible use in Traid.

Every project must be reviewed against all 45 sections below. No section
may be silently skipped.

If evidence cannot be found or verified, explicitly record one of:

-   Not implemented
-   Not found
-   Cannot verify

The purpose is to avoid duplicate work, compare projects consistently,
identify reusable components, and prevent unnecessary architecture
complexity.

## Mandatory Evidence Rule

For every applicable section, provide:

1.  Question / area being evaluated
2.  Evidence from repository code, configuration, documentation, tests,
    commits, issues, or other verifiable project material
3.  Analysis
4.  Implication for Traid
5.  Classification where relevant: REUSE / ADAPT / REFERENCE ONLY /
    REJECT

README claims alone are not sufficient when the underlying
implementation can be inspected.

## 45 Mandatory Audit Sections

### 1. Project Purpose

What problem does the project actually solve and what is its intended
scope?

### 2. Overall Architecture

Identify the architecture, major components, service boundaries, and
system flow.

### 3. Repository Structure

Review the important directories, modules, packages, and files and
explain their responsibilities.

### 4. Data Ingestion

Identify all incoming data sources and how data enters the system.

### 5. REST / WebSocket / Connectivity

Review REST APIs, WebSockets, retry logic, reconnect behavior,
rate-limit handling, and connection management.

### 6. Database and Storage

Identify databases, caches, schemas, persistence patterns, retention,
and storage responsibilities.

### 7. Analytics

Identify the exact deterministic analytics, indicators, calculations,
transformations, and derived metrics implemented.

### 8. Signal Engine

Explain how signals are created, scored, combined, filtered, and
classified.

### 9. Whale / Smart Money Intelligence

Review wallet tracking, large positions, large trades, scoring,
behavioral tracking, and smart-money logic.

### 10. News / Macro / External Intelligence

Identify news, macroeconomic, sentiment, ETF, social, regulatory, or
other external information sources and processing.

### 11. Strategy Engine

Explain strategy definitions, entry/exit logic, setup detection, rule
evaluation, and strategy orchestration.

### 12. Backtesting

Review the backtesting architecture and methodology.

### 13. Trading Realism

Check fees, funding, slippage, latency assumptions, lookahead bias
prevention, execution assumptions, and other realism controls.

### 14. AI / LLM Layer

Identify where AI or LLMs are used and what responsibilities they have.

### 15. Deterministic vs AI Boundaries

Determine whether deterministic financial calculations and critical
decisions are correctly separated from AI interpretation.

### 16. Risk Management

Review position sizing, leverage, stops, R/R, exposure controls, loss
limits, and other risk mechanisms.

### 17. Risk Gate

Determine whether a true deterministic trade-blocking gate exists,
whether it can be bypassed, and how failures are handled.

### 18. Dashboard

Review the information presented to the user and how operational state
is exposed.

### 19. Logging

Review application logs, error logs, structured logging, and diagnostic
information.

### 20. Monitoring

Review runtime monitoring, service health, system metrics, and
operational visibility.

### 21. Data Quality

Review freshness, missing-data handling, validation, stale-data
detection, reconciliation, and bad-data protection.

### 22. Tests

Identify unit, integration, end-to-end, regression, backtest, and other
tests.

### 23. Test Quality / Coverage

Evaluate what important behavior is actually protected by tests and
identify major gaps.

### 24. Deployment

Review Docker, containers, cloud deployment, local execution, CI/CD,
environment setup, and operational dependencies.

### 25. Configuration

Review configuration structure, environment variables, feature flags,
runtime settings, and portability.

### 26. Secrets Management

Review API keys, credentials, secret storage, accidental exposure risk,
and environment handling.

### 27. Dependencies and Technology Stack

List important languages, frameworks, libraries, infrastructure, and
external services.

### 28. Code Quality

Evaluate readability, organization, typing, validation, error handling,
duplication, and maintainability.

### 29. Coupling and Modularity

Determine how tightly components are coupled and how easily individual
pieces can be reused or replaced.

### 30. Maintenance Status

Review recent commits, development activity, project maturity, release
activity, and signs of abandonment.

### 31. Issues and Known Problems

Review meaningful open/closed issues, documented limitations, bugs,
technical debt, and unresolved risks.

### 32. License

Identify the license and what it permits or restricts for Traid reuse,
modification, and distribution.

### 33. Project Strengths

Identify concrete strengths supported by implementation evidence.

### 34. Project Weaknesses

Identify concrete weaknesses, missing capabilities, design problems, and
operational risks.

### 35. Traid Comparative Assessment

Explain what the project does better than Traid's planned architecture
and what Traid is designed to do better.

### 36. What We Should Take

List the exact components, modules, algorithms, patterns, schemas,
tests, or ideas worth taking.

### 37. What We Should Not Take

List what should not be imported or copied and explain why.

### 38. What Traid Should Build Itself

Identify capabilities where the external project's implementation is
unsuitable, missing, risky, or unnecessarily complex.

### 39. Estimated Saved Work

Estimate which Traid workstreams could be eliminated or shortened
through reuse or adaptation. Clearly separate verified savings from
rough estimates.

### 40. UI / UX Audit

Review dashboard design, layout, navigation, information hierarchy,
charts, interaction patterns, responsiveness, usability, visual density,
and useful design ideas for Traid.

### 41. Security Audit

Review authentication, authorization, permissions, input validation,
secret handling, exposed services, dependency risks, and obvious
security weaknesses.

### 42. Performance and Scalability

Identify likely bottlenecks, high-volume behavior, concurrency patterns,
caching, database scaling concerns, and limitations under increased
market data load.

### 43. Failure Handling and Reliability

Review behavior during WebSocket disconnects, API failures, stale feeds,
rate limits, database failures, process restarts, partial service
failure, recovery, and degraded operation.

### 44. Observability

Review logs, metrics, traces, health checks, alerts, auditability,
data-status visibility, and ability to determine why the system produced
a result.

### 45. Traid Integration Map

Map every recommended reusable or adaptable component to the exact Traid
subsystem where it would belong. Record dependencies, integration
difficulty, architecture impact, risks, and expected benefit.

## Required Classification

Every meaningful candidate component must receive one classification:

-   **REUSE** --- suitable for direct reuse with minimal change.
-   **ADAPT** --- valuable but requires modification for Traid.
-   **REFERENCE ONLY** --- useful as an implementation/design reference
    but should not be imported.
-   **REJECT** --- should not be used because its cost, quality, risk,
    license, architecture, or complexity is unsuitable.

## Anti-Duplication Rule

Before recommending that Traid build a capability from scratch, check
whether the audited project already provides a suitable implementation.

Before recommending reuse, verify that integration cost does not exceed
the work saved.

Do not merge repositories simply because they contain useful features.
Prefer one coherent Traid architecture and selectively reuse or adapt
compatible components.

## Completion Rule

An audit is COMPLETE only when all 45 numbered sections have an explicit
answer.

Runtime execution, benchmarks, or integration tests that have not
actually been performed must never be presented as verified results.

Each project receives its own independent Markdown audit file using this
exact standard.
