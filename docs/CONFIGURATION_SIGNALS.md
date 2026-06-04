# Configuration & Environment Signals

## Scope

Configuration signals are **repository-local indicators about environment/configuration hygiene**.
They answer the question: "Is the project's configuration surface well-documented and reproducible?"

## What configuration signals are

- Environment file detected without corresponding example file (`.env` without `.env.example`)
- Configuration hygiene gaps that affect setup, onboarding, and environment parity

## What configuration signals are NOT

- **Not** secret scanning — no credential validation or verification
- **Not** security findings — TD-CONFIG is distinct from TD-SEC
- **Not** config hardening — no policy enforcement engine
- **Not** build/deployment signals — distinct from TD-BUILD
- **Not** policy-as-code — no configuration policy engine

## Signal governance (v3.19.0)

Configuration signals are governed through `SignalFamily.CONFIGURATION`.
The adapter in `configuration_adapters.py` converts environment evidence
into `GovernedSignal` with FINDING disposition.

The analyzer uses `output_behavior()` for promotion decisions.

v3.19.0 emits FINDING only for configuration — no advisory or informational
configuration signals.

`.env.example` alone is a skip/no-signal condition.

See `docs/SIGNAL_GOVERNANCE.md` for the full governance model.
