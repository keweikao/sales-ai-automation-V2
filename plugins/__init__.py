"""
Sales AI Plugins.

Available plugins:
- sales-core: Core sales analysis skills (context, summary, CRM)
- sales-meddic: MEDDIC methodology analysis (buyer, seller, coaching)
"""

from pathlib import Path

PLUGINS_DIR = Path(__file__).parent


def get_available_plugins() -> list[str]:
    """Return list of available plugin directory names."""
    plugins = []
    for item in PLUGINS_DIR.iterdir():
        if item.is_dir() and not item.name.startswith("_"):
            if (item / "plugin.py").exists() or (item / "__init__.py").exists():
                plugins.append(item.name)
    return plugins


__all__ = ["PLUGINS_DIR", "get_available_plugins"]
