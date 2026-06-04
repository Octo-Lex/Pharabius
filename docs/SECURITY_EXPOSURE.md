# Security Exposure Signals

## Scope

Pharabius produces local security-exposure evidence by detecting risk-sensitive
keywords and paths in repository contents. It does **not** perform external
security analysis.

## What security exposure signals are

Security exposure signals are **repository-local indicators**. They represent:

- Keywords associated with compliance-sensitive domains (PII, GDPR, HIPAA, PCI, retention, patient)
- Risk-sensitive file paths (auth, session, billing, etc.)
- Potential exposure based on keyword evidence

## What security exposure signals are NOT

- **Not** confirmed vulnerabilities
- **Not** CVE lookups or exploitability analysis
- **Not** SAST (Static Application Security Testing)
- **Not** DAST (Dynamic Application Security Testing)
- **Not** taint analysis
- **Not** secret validation against external services
- **Not** credential verification

No output from Pharabius should be interpreted as a confirmed security vulnerability
or exploitability claim.

## Signal governance (v3.17.0)

Security exposure signals are governed through `SignalFamily.SECURITY`.
Adapters in `security_adapters.py` convert evidence into `GovernedSignal` instances
with deterministic dispositions.

Compliance exposure findings are governed under `SignalFamily.SECURITY` in v3.17.0
because the migrated analyzer represents security/compliance exposure indicators,
while preserving `category="TD-COMP"`.

The analyzer uses `output_behavior()` for promotion decisions instead of
hardcoded branching. Output before and after migration is identical.

### Family boundary with test health

`_analyze_risk_sensitive_without_tests` is governed under `SignalFamily.TEST`
(v3.14.0) and produces `TD-SEC` findings. It is NOT part of the security family.

Security informational signals (path/keyword detection) are summary-only:
they appear in signal summaries but do not create findings, advisories, or
work packages.

### Compliance keyword set

The exact compliance keyword set is:

```python
{"pii", "gdpr", "hipaa", "pci", "retention", "patient"}
```

No keyword is added, removed, or reclassified in v3.17.0.

See `docs/SIGNAL_GOVERNANCE.md` for the full governance model.
