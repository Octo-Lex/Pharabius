"""Ticket draft generation helpers.

Pure deterministic functions for ticket ID mapping and filename generation.
No I/O, no network, no mutation.
"""

from __future__ import annotations


def ticket_id_for_work_package(work_package_id: str) -> str:
    """Map a work package ID to a deterministic ticket draft ID.

    WP-001 → TICKET-WP-001
    """
    return f"TICKET-{work_package_id}"


def ticket_id_for_finding(finding_id: str) -> str:
    """Map a finding ID to a deterministic ticket draft ID (reserved).

    TD-ARCH-001 → TICKET-TD-ARCH-001
    """
    return f"TICKET-{finding_id}"


def ticket_filename(ticket_id: str) -> str:
    """Map a ticket ID to its Markdown filename.

    TICKET-WP-001 → TICKET-WP-001.md
    """
    return f"{ticket_id}.md"
