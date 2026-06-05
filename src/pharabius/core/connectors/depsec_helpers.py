"""Shared helpers for dependency/security connectors.

Provides:
- assign_depsec_confidence: vulnerability scanner confidence (locator + vuln ID + message)
- assign_sbom_confidence: SBOM connector confidence (package + version/purl + location)
- build_package_coordinates: standardized package metadata dict
"""

from __future__ import annotations

from pharabius.schemas.evidence import EvidenceItem

# ---------------------------------------------------------------------------
# Confidence levels and reasons
# ---------------------------------------------------------------------------

CONFIDENCE_HIGH = "High"
CONFIDENCE_MEDIUM = "Medium"
CONFIDENCE_LOW = "Low"

# Depsec (vulnerability scanner) reasons
REASON_LOCATOR_VULN_MESSAGE = "locator_vulnerability_id_and_message_present"
REASON_LOCATOR_OR_VULN = "locator_or_vulnerability_id_present"
REASON_WEAK_VULN_METADATA = "weak_vulnerability_metadata"

# SBOM reasons
REASON_SBOM_NAME_VERSION_LOCATION = "sbom_name_version_and_location_present"
REASON_SBOM_NAME_OR_PURL = "sbom_name_or_purl_present"
REASON_SBOM_WEAK_METADATA = "weak_sbom_package_metadata"


# ---------------------------------------------------------------------------
# Vulnerability scanner confidence
# ---------------------------------------------------------------------------


def assign_depsec_confidence(
    *,
    has_locator: bool,
    has_vulnerability_id: bool,
    has_message: bool,
) -> tuple[str, str]:
    """Assign confidence for vulnerability scanner evidence.

    Args:
        has_locator: Whether a package name, purl, target, or file path is present.
        has_vulnerability_id: Whether a CVE/vulnerability ID is present.
        has_message: Whether a title or description is present.

    Returns:
        Tuple of (confidence_level, confidence_reason).
    """
    if has_locator and has_vulnerability_id and has_message:
        return CONFIDENCE_HIGH, REASON_LOCATOR_VULN_MESSAGE
    elif has_locator or has_vulnerability_id:
        return CONFIDENCE_MEDIUM, REASON_LOCATOR_OR_VULN
    else:
        return CONFIDENCE_LOW, REASON_WEAK_VULN_METADATA


# ---------------------------------------------------------------------------
# SBOM connector confidence
# ---------------------------------------------------------------------------


def assign_sbom_confidence(
    *,
    has_name: bool,
    has_version_or_purl: bool,
    has_location: bool,
) -> tuple[str, str]:
    """Assign confidence for SBOM evidence.

    SBOM evidence does not have vulnerability IDs. Confidence is based on
    package completeness: name + version/purl + source location.

    Args:
        has_name: Whether a package name is present.
        has_version_or_purl: Whether a version or purl is present.
        has_location: Whether a real file/path location exists.

    Returns:
        Tuple of (confidence_level, confidence_reason).
    """
    if has_name and has_version_or_purl and has_location:
        return CONFIDENCE_HIGH, REASON_SBOM_NAME_VERSION_LOCATION
    elif has_name or has_version_or_purl:
        return CONFIDENCE_MEDIUM, REASON_SBOM_NAME_OR_PURL
    else:
        return CONFIDENCE_LOW, REASON_SBOM_WEAK_METADATA


# ---------------------------------------------------------------------------
# Package coordinates
# ---------------------------------------------------------------------------


def build_depsec_coordinates(
    *,
    pkg_name: str = "",
    installed_version: str = "",
    fixed_version: str = "",
    purl: str = "",
    severity: str = "",
    primary_url: str = "",
) -> dict[str, str]:
    """Build standardized package coordinates for vulnerability evidence."""
    coords: dict[str, str] = {}
    if pkg_name:
        coords["pkg_name"] = pkg_name
    if installed_version:
        coords["installed_version"] = installed_version
    if fixed_version:
        coords["fixed_version"] = fixed_version
    if purl:
        coords["purl"] = purl
    if severity:
        coords["severity"] = severity
    if primary_url:
        coords["primary_url"] = primary_url
    return coords


def build_sbom_coordinates(
    *,
    pkg_name: str = "",
    version: str = "",
    pkg_type: str = "",
    language: str = "",
    purl: str = "",
    licenses: list[str] | None = None,
    found_by: str = "",
) -> dict[str, str | list[str]]:
    """Build standardized package coordinates for SBOM evidence."""
    coords: dict[str, str | list[str]] = {}
    if pkg_name:
        coords["pkg_name"] = pkg_name
    if version:
        coords["version"] = version
    if pkg_type:
        coords["pkg_type"] = pkg_type
    if language:
        coords["language"] = language
    if purl:
        coords["purl"] = purl
    if licenses:
        coords["licenses"] = licenses
    if found_by:
        coords["found_by"] = found_by
    return coords


# ---------------------------------------------------------------------------
# Apply confidence to evidence item
# ---------------------------------------------------------------------------


def apply_confidence_with_reason(
    item: EvidenceItem,
    confidence: str,
    reason: str,
) -> EvidenceItem:
    """Apply confidence and reason to an evidence item via metadata.

    Returns a new EvidenceItem with confidence and confidence_reason set.
    """
    updated_metadata = {**item.metadata, "confidence_reason": reason}
    return item.model_copy(
        update={
            "confidence": confidence,
            "metadata": updated_metadata,
        }
    )
