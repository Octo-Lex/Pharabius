"""Signal governance foundation.

Platform-level signal representation and policy.
Domain-specific IRs (runtime, dependency, etc.) adapt into GovernedSignal
via family-specific adapters. Signal policy controls promotion to
findings, advisories, and informational output.
"""

from __future__ import annotations

from pharabius.core.signals.models import (
    GovernedSignal,
    SignalDisposition,
    SignalFamily,
)
from pharabius.core.signals.policy import (
    is_informational,
    is_reportable,
    should_create_advisory,
    should_create_finding,
    should_create_work_package,
)

__all__ = [
    "GovernedSignal",
    "SignalDisposition",
    "SignalFamily",
    "is_informational",
    "is_reportable",
    "should_create_advisory",
    "should_create_finding",
    "should_create_work_package",
]
