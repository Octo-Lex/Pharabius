# Pharabius Architecture

## Architecture Style

Pharabius v1 uses a modular monolith architecture.

The system runs as a local CLI and repository analysis engine. It produces `.ai-debt/` artifacts and does not modify production code by default.

## Current Layers

```text
CLI
 ↓
Core Runtime
 ↓
Schemas / Writers
 ↓
Repository-local Output Contract
```

## Allowed Dependencies

| Layer               | May Import                                      |
| ------------------- | ----------------------------------------------- |
| `pharabius.cli`     | `pharabius.core`                                |
| `pharabius.core`    | `pharabius.schemas`, future `pharabius.writers` |
| `pharabius.writers` | `pharabius.schemas`                             |
| `pharabius.schemas` | Standard library, Pydantic                      |

## Forbidden Dependencies

| Source              | Forbidden Target |
| ------------------- | ---------------- |
| `pharabius.schemas` | `pharabius.cli`  |
| `pharabius.schemas` | `pharabius.core` |
| `pharabius.core`    | `pharabius.cli`  |
| `pharabius.writers` | `pharabius.cli`  |
| `pharabius.writers` | `pharabius.core` |

## Architectural Rule

Lower-level modules must not depend on higher-level orchestration modules.

Schemas are the most stable layer and must remain free of runtime orchestration logic.

## Drift Prevention

Architecture compliance is enforced by:

```bash
lint-imports
```

The CI pipeline must fail if forbidden imports are introduced.
