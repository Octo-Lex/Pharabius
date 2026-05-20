# Security-Focused Technical Debt Handoff

## Repository

{{ repository_section }}

## Executive Summary

{{ executive_summary }}

## Security-First Review Priority

This handoff uses the **security-sensitive** preset. Security and compliance
findings (TD-SEC, TD-COMP) should be reviewed first.

{{ top_risks_table }}

## Recommended First Actions

{{ recommended_first_actions }}

## Security Escalation Guide

| Category | Escalation |
|---|---|
| TD-SEC (security) | Security team review required before any action |
| TD-COMP (compliance) | Legal/compliance review for keyword interpretation |
| TD-DATA (data management) | Data governance review if PII/sensitive data involved |
| All others | Team lead triage |

## Remediation Roadmap

See `remediation-roadmap.md`.

## Product Engineering Decisions Needed

{{ pet_decisions }}

## Risks and Cautions

{{ risks_and_cautions }}

> **No code modification by tooling.** Pharabius does not modify production
> code. All remediation is implemented by Product Engineering.

## Uncertainties and Missing Evidence

{{ uncertainties }}

## Generated Artifacts

{{ generated_artifacts }}

## Review Checklist

- [ ] Security findings (TD-SEC, TD-COMP) reviewed with security team.
- [ ] Evidence IDs verified against source code.
- [ ] No credential or secret handling changes without approval.
- [ ] Inferred business impact validated with Product Engineering.
- [ ] Work packages assigned to owners with security awareness.
