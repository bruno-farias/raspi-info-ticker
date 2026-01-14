"""Configuration module for the info ticker."""

from .manager import ConfigManager, config_manager
from .schemas import (
    AppConfig,
    AuthConfig,
    WebServerConfig,
    DisplayConfig,
    LayoutConfig,
    PluginConfigs,
    WeatherConfig,
    CurrencyConfig,
    CryptoConfig,
    StockConfig,
    ClockConfig,
    WidgetConfig,
    DashboardConfig,
    AuthProvider,
    LayoutType,
    DisplayMode
)

__all__ = [
    "ConfigManager",
    "config_manager",
    "AppConfig",
    "AuthConfig",
    "WebServerConfig",
    "DisplayConfig",
    "LayoutConfig",
    "PluginConfigs",
    "WeatherConfig",
    "CurrencyConfig",
    "CryptoConfig",
    "StockConfig",
    "ClockConfig",
    "WidgetConfig",
    "DashboardConfig",
    "AuthProvider",
    "LayoutType",
    "DisplayMode"
]