"""Configuration signal adapters.

Translate configuration/environment evidence into platform-level GovernedSignal
instances. Configuration signals are environment/configuration hygiene indicators.

v3.19.0: Adoption release — adapter matches existing behavior exactly.
Only env-without-example produces FINDING disposition.
No advisory or informational configuration signals in v3.19.0.

Configuration signals are NOT security signals. They do not perform
secret validation, credential verification, or security claims.
"""

from __future__ import annotations

from pharabius.core.signals.models import (
    GovernedSignal,
    SignalDisposition,
    SignalFamily,
    make_signal_id,
)


def configuration_env_without_example_to_signal(
    evidence_items: list[object],
) -> GovernedSignal:
    """Adapt env-without-example evidence into a GovernedSignal (FINDING).

    Triggered when .env or .env.local is detected but .env.example is absent.
    Disposition matches existing _analyze_env_without_example behavior exactly.
    """
    ev_ids = [getattr(item, "evidence_id", str(i)) for i, item in enumerate(evidence_items)]

    signal_id = make_signal_id("configuration", "env_without_example", ev_ids)

    return GovernedSignal(
        signal_id=signal_id,
        family=SignalFamily.CONFIGURATION,
        kind="env_without_example",
        disposition=SignalDisposition.FINDING,
        category="TD-CONFIG",
        severity="Medium",
        confidence="High",
        evidence_ids=ev_ids,
        source_signal_ids=[],
        title="Environment configuration detected without example file",
        summary=(
            "An environment configuration file was detected, but no `.env.example` file was found."
        ),
        explanation=(
            "Missing environment examples make setup, onboarding, and environment "
            "parity harder to verify."
        ),
        metadata={
            "spec_kind": "env_without_example",
            "env_files": [
                getattr(item, "location", None) and getattr(item.location, "file", "")
                for item in evidence_items
            ],
        },
    )
