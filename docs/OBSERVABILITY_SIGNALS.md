# Observability Signals

## Scope

Observability signals are **repository-local indicators about logging, metrics,
tracing, monitoring, alerting, or health-check evidence when already detected**.

They answer the question: "Does deployment evidence suggest observability coverage?"

## What observability signals are

- Deployment or infrastructure files detected without any observability keyword evidence (`logging`, `monitoring`, `tracing`, `alert`, `metrics`)
- A finding about potentially missing operational visibility, based on evidence absence
- Conservative: CI-only workflows are excluded; only real deployment/infra evidence triggers

## What observability signals are NOT

- **Not** runtime telemetry collection
- **Not** external monitoring system queries
- **Not** SLO/SLA analysis
- **Not** operational maturity scoring
- **Not** production-readiness certification
- **Not** health-check endpoint inference (unless already implemented)
- **Not** build, configuration, or security findings

## Signal governance (v3.20.0)

Observability signals are governed through `SignalFamily.OBSERVABILITY`.
The adapter in `observability_adapters.py` converts deployment/infrastructure
evidence into `GovernedSignal` with FINDING disposition.

The analyzer uses `output_behavior()` for promotion decisions.

v3.20.0 emits FINDING only for observability — no advisory or informational
observability signals.

TD-OBS trigger is the absence of existing `risk_sensitive_keyword_detected`
evidence matching the observability keyword set. No new keyword scanning is
added.

CI-only deployment evidence (`.github/workflows/`, `.gitlab-ci`) is excluded
from TD-OBS.

See `docs/SIGNAL_GOVERNANCE.md` for the full governance model.
