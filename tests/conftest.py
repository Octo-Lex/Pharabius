"""Pytest configuration for test collection.

Adds the test fixtures directory to sys.path for cross-platform
compatibility. On Ubuntu, implicit namespace packages resolve
`from tests.fixtures...` naturally. On Windows, they don't.
This conftest ensures both platforms find the fixtures.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure tests/ is importable as a package root for cross-test imports
_tests_dir = str(Path(__file__).parent)
if _tests_dir not in sys.path:
    sys.path.insert(0, _tests_dir)
