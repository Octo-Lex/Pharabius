"""Runtime version pin detection — backward compatibility shim.

All logic moved to pharabius.core.runtime package in v3.9.0.
This module re-exports the public API for backward compatibility.
"""

from pharabius.core.runtime import detect_runtime_version_pins

__all__ = ["detect_runtime_version_pins"]
