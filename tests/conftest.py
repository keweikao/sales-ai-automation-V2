"""
Root test configuration.

Sets up Python paths for all test modules.
"""

import sys
from pathlib import Path

# Project root directory
project_root = Path(__file__).parent.parent

# Add paths to Python path for imports
paths_to_add = [
    str(project_root),
    str(project_root / "src"),
    str(project_root / "analysis-service"),
    str(project_root / "api-gateway"),
    str(project_root / "infrastructure"),
]

for path in paths_to_add:
    if path not in sys.path:
        sys.path.insert(0, path)
