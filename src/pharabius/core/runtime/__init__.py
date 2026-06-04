"""Runtime evidence normalization and signal governance.

v3.9.0: Package split from runtime_parsers.py into governed signal pipeline.

Public API:
    detect_runtime_version_pins(root, builder) — scanner-facing entry point
"""

from pharabius.core.runtime.detector import detect_runtime_version_pins

__all__ = ["detect_runtime_version_pins"]
