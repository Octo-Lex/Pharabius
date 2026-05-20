# Compliance-Focused Technical Debt Handoff

## Repository

{{ repository_section }}

## Executive Summary

{{ executive_summary }}

## Compliance Review Priority

This handoff uses the **compliance-sensitive** preset. Compliance (TD-COMP),
security (TD-SEC), data management (TD-DATA), and process (TD-PROCESS)
findings require review with legal/compliance team.

{{ top_risks_table }}

## Recommended First Actions

{{ recommended_first_actions }}

## Compliance Escalation Guide

| Category | Required Review |
|---|---|
| TD-COMP (compliance) | Legal/compliance team |
| TD-SEC (security) | Security team + compliance |
| TD-DATA (data management) | Data governance review |
| TD-PROCESS (process) | Process owner review |

## Remediation Roadmap

See `remediation-roadmap.md`.

## Product Engineering Decisions Needed

{{ pet_decisions }}

## Risks and Cautions

{{ risks_and_cautions }}

## Uncertainties and Missing Evidence

{{ uncertainties }}

## Generated Artifacts

{{ generated_artifacts }}

## Review Checklist

- [ ] Compliance findings reviewed with legal/compliance team.
- [ ] Evidence IDs verified against source code.
- [ ] Audit trail documented for all accepted changes.
- [ ] No data handling changes without data governance review.
- [ ] Work packages assigned with compliance awareness.
