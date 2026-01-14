"""Raspi Info Ticker - Modern plugin-based information display system."""

__version__ = "2.0.0"
__author__ = "System"
__description__ = "A modular information display system for Raspberry Pi with e-paper display"

from .plugins import plugin_registry, BasePlugin
from .config import config_manager

__all__ = [
    "plugin_registry",
    "BasePlugin",
    "config_manager",
    "__version__",
    "__author__",
    "__description__"
]