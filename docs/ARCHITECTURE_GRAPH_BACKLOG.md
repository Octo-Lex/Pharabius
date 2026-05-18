# Architecture Graph Backlog

Prioritized list of issues and improvements discovered during field validation.

## P0 — Blockers

None.

## P1 — Correctness Issues

| ID | Issue | Affected | Fix | Target |
|---|---|---|---|---|
| FN-001 | Monorepo packages/* node collapse | Ghostwire | Split by package.json subdirectories | v0.6.0 |
| FN-002 | Monorepo apps/*, packages/* node collapse | Craft-Agents | Same as FN-001 | v0.6.0 |
| FN-003 | Rust use import detection missing | Symbiot, AIF | Add Rust pattern to scanner IMPORT_PATTERNS | v0.6.0 |
| FN-004 | Sub-package collapse prevents boundary detection | validation-policy | Split src/pkg/sub into separate nodes | v0.6.0 |

### FN-001/FN-002/FN-004 — Monorepo/Sub-Package Node Derivation

**Problem**: Node derivation groups by first directory level under src/ (or repo root). For monorepos using packages/* or sub-package layouts (src/myapp/cli), all files collapse into a single node.

**Proposed fix**:
- For TypeScript/JS: detect package.json in subdirectories of packages/, apps/ to create individual package nodes
- For Python: detect __init__.py in subdirectories under a shared parent to create sub-package nodes
- Requires design decision on monorepo detection strategy

**Risk**: Medium — changes node derivation logic, affects ID stability

### FN-003 — Rust Import Detection

**Problem**: Scanner IMPORT_PATTERNS only matches Python/JS patterns. Rust `use crate::module::item` and `use module::item` not matched.

**Proposed fix**: Add `re.compile(r"^\s*use\s+([\w:]+)", re.MULTILINE)` to IMPORT_PATTERNS in scanner.py.

**Risk**: Low — additive change to scanner, no existing behavior affected.

## P2 — Noise Reduction

| ID | Issue | Fix | Target |
|---|---|---|---|
| NR-001 | Test-to-source edges not distinguished from production edges | Mark test-scope edges or reduce confidence | v0.6.0 |
| NR-002 | TypeScript import type treated as runtime dependency | Document limitation, consider filtering | v0.6.0 |
| NR-003 | Relative import noise in limitations count (66 for elephant-rock-platform, 420 for Ghostwire, 1996 for Craft-Agents) | Document as expected behavior for relative imports | v0.5.2 |

## P3 — Documentation

| ID | Issue | Fix | Target |
|---|---|---|---|
| DOC-001 | Node derivation strategy not documented | Add section to ARCHITECTURE.md | v0.5.2 |
| DOC-002 | Monorepo limitation not in KNOWN_LIMITATIONS.md | Add items for monorepo node collapse and Rust imports | v0.5.2 |
| DOC-003 | Graph validation results template not in docs | Add to templates/ | v0.5.2 |
