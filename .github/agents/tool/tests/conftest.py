"""
Shared pytest configuration for Tier D tests

Centralizes import path configuration to avoid repetition
across test files.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
# This allows tests to import from analysis/, models/, etc.
tool_root = Path(__file__).parent.parent
sys.path.insert(0, str(tool_root))
