"""Where Bonsai keeps its files, following the XDG base directories."""

import os
from pathlib import Path


def cache_dir() -> Path:
    """$XDG_CACHE_HOME/bonsai-xiv: ~/.cache/bonsai-xiv by default."""
    return _xdg("XDG_CACHE_HOME", ".cache") / "bonsai-xiv"


def config_dir() -> Path:
    """$XDG_CONFIG_HOME/bonsai-xiv: ~/.config/bonsai-xiv by default."""
    return _xdg("XDG_CONFIG_HOME", ".config") / "bonsai-xiv"


def _xdg(variable: str, default: str) -> Path:
    directory = os.environ.get(variable)
    return Path(directory) if directory else Path.home() / default
