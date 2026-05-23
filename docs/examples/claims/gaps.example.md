# Gap and Question Registry

**Total gaps**: 2

## GAP-0001 — Blocking

- **Type**: security
- **Confidence**: Low
- **Statement**: No evidence of input validation or sanitization on the payment processing endpoint.
- **Validation Question**: Has input validation been reviewed for payment endpoints?
- **Linked claim**: CLM-000004
- **Linked findings**: TD-SEC-001
- **Linked work packages**: WP-003
- **Reason**: Finding is security-sensitive and implementation semantics cannot be safely inferred from repository evidence alone.

## GAP-0002 — Non-blocking

- **Type**: test
- **Confidence**: Low
- **Statement**: No integration tests found for the refund workflow.
- **Validation Question**: Are refund workflow integration tests maintained elsewhere?
- **Linked claim**: CLM-000005
- **Linked findings**: TD-TEST-002
- **Linked work packages**: (none)
- **Reason**: Lower-priority finding. Coverage gap should be reviewed but does not block ongoing work.
