# Architecture Risk Signals

## Scope

Architecture risk signals are **graph-derived repository-local indicators**. They are produced by reading `architecture-graph.json` and converting detected cycles and boundary violations into TD-ARCH findings.

## What architecture signals are

- Circular dependency detections (cycles with ≥ 2 nodes and evidence)
- Boundary policy violation detections (layer violations with evidence, rule, and policy)
- Capped at 20 findings per type to prevent noise

## What architecture signals are NOT

- **Not** high-coupling findings — coupling metrics do not create findings
- **Not** unresolved-import findings
- **Not** external-import findings
- **Not** architecture scores or ratings
- **Not** graph schema changes

## Signal governance (v3.18.0)

Architecture risk signals are governed through `SignalFamily.ARCHITECTURE`.
Adapters in `architecture_adapters.py` convert `ArchFindingSpec` instances
into `GovernedSignal` with FINDING disposition.

The analyzer uses `output_behavior()` for promotion decisions. Routing uses
`spec.kind` (stable field), not title text.

`architecture_analyzer.py` is unchanged (except the `kind` field on
`ArchFindingSpec`). The governance boundary is in `analyzer.py`.

v3.18.0 emits FINDING only for architecture — no informational architecture signals.

See `docs/SIGNAL_GOVERNANCE.md` for the full governance model.
