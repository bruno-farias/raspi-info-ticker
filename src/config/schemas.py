"""Configuration schemas for the info ticker system."""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum


class AuthProvider(str, Enum):
    """Supported authentication providers."""
    BASIC = "basic"
    OAUTH = "oauth"
    OIDC = "oidc"
    NONE = "none"


class LayoutType(str, Enum):
    """Layout types for display."""
    GRID = "grid"
    LIST = "list"
    CAROUSEL = "carousel"
    CUSTOM = "custom"


class DisplayMode(str, Enum):
    """Display output modes."""
    EPAPER = "epaper"
    TERMINAL = "terminal"
    WEB = "web"
    ALL = "all"


class WeatherConfig(BaseModel):
    """Configuration for weather plugin."""
    enabled: bool = True
    update_interval: int = 300  # 5 minutes
    cache_ttl: int = 600  # 10 minutes
    priority: int = 1
    api_key: str = Field(..., description="OpenWeatherMap API key")
    cities: List[Dict[str, str]] = Field(
        default=[{"name": "London", "country": "UK"}],
        description="List of cities to monitor"
    )
    current_city_index: int = Field(default=0, description="Currently selected city index")
    units: str = Field(default="metric", description="Units: metric, imperial, kelvin")
    language: str = Field(default="en", description="Language code")
    show_forecast: bool = Field(default=False, description="Show weather forecast")


class CurrencyConfig(BaseModel):
    """Configuration for currency plugin."""
    enabled: bool = True
    update_interval: int = 60  # 1 minute
    cache_ttl: int = 300  # 5 minutes
    priority: int = 2
    api_key: str = Field(..., description="Currency API key")
    base_currency: str = Field(default="USD", description="Base currency")
    target_currencies: List[str] = Field(
        default=["EUR", "GBP", "JPY", "BRL"],
        description="Currencies to track"
    )
    # Support for multiple currency configurations
    currencies: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="List of currency configurations (base + targets)"
    )
    decimal_places: int = Field(default=4, description="Decimal places for rates")
    show_change: bool = Field(default=True, description="Show 24h change")


class CryptoConfig(BaseModel):
    """Configuration for cryptocurrency plugin."""
    enabled: bool = True
    update_interval: int = 30  # 30 seconds
    cache_ttl: int = 60  # 1 minute
    priority: int = 3
    api_key: Optional[str] = Field(None, description="API key (optional for some providers)")
    provider: str = Field(default="coingecko", description="API provider")
    cryptocurrencies: List[str] = Field(
        default=["bitcoin", "ethereum"],
        description="Cryptocurrencies to track"
    )
    vs_currencies: List[str] = Field(
        default=["usd", "eur"],
        description="Comparison currencies"
    )
    show_market_cap: bool = Field(default=False, description="Show market cap")
    show_volume: bool = Field(default=False, description="Show 24h volume")
    show_change_24h: bool = Field(default=True, description="Show 24h price change")
    show_change_7d: bool = Field(default=False, description="Show 7d price change")


class StockConfig(BaseModel):
    """Configuration for stock market plugin."""
    enabled: bool = False
    update_interval: int = 60
    cache_ttl: int = 120
    priority: int = 4
    api_key: Optional[str] = Field(default=None, description="Stock API key")
    symbols: List[str] = Field(
        default=["AAPL", "GOOGL", "MSFT"],
        description="Stock symbols to track"
    )
    show_premarket: bool = Field(default=False, description="Show pre-market data")
    show_afterhours: bool = Field(default=False, description="Show after-hours data")


class ClockConfig(BaseModel):
    """Configuration for clock plugin."""
    enabled: bool = True
    update_interval: int = 1  # 1 second
    cache_ttl: int = 0  # No caching
    priority: int = 0
    timezone: Optional[str] = Field(None, description="Timezone (e.g., 'UTC', 'US/Eastern')")
    format_24h: bool = Field(default=True, description="Use 24-hour format")
    show_date: bool = Field(default=True, description="Show date")
    show_seconds: bool = Field(default=True, description="Show seconds")
    show_day_name: bool = Field(default=False, description="Show day name")
    show_week_number: bool = Field(default=False, description="Show week number")
    date_format: str = Field(default="%Y-%m-%d", description="Date format string")


class AuthConfig(BaseModel):
    """Authentication configuration."""
    provider: AuthProvider = Field(default=AuthProvider.BASIC)
    secret_key: str = Field(..., description="Secret key for JWT tokens")

    # Basic auth
    username: Optional[str] = Field(None, description="Basic auth username")
    password_hash: Optional[str] = Field(None, description="Hashed password")

    # OAuth/OIDC
    client_id: Optional[str] = Field(None, description="OAuth client ID")
    client_secret: Optional[str] = Field(None, description="OAuth client secret")
    authorization_url: Optional[str] = Field(None, description="OAuth authorization URL")
    token_url: Optional[str] = Field(None, description="OAuth token URL")
    userinfo_url: Optional[str] = Field(None, description="OIDC userinfo URL")
    redirect_uri: Optional[str] = Field(None, description="OAuth redirect URI")

    # Session
    session_timeout: int = Field(default=3600, description="Session timeout in seconds")
    remember_me_duration: int = Field(default=604800, description="Remember me duration (7 days)")


class WebServerConfig(BaseModel):
    """Web server configuration."""
    enabled: bool = Field(default=True, description="Enable web interface")
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8080, description="Server port")
    ssl_enabled: bool = Field(default=False, description="Enable SSL/TLS")
    ssl_cert: Optional[str] = Field(None, description="SSL certificate path")
    ssl_key: Optional[str] = Field(None, description="SSL key path")
    cors_origins: List[str] = Field(default=["*"], description="CORS allowed origins")
    max_connections: int = Field(default=100, description="Maximum concurrent connections")


class DisplayConfig(BaseModel):
    """Display configuration."""
    mode: DisplayMode = Field(default=DisplayMode.ALL)
    refresh_interval: int = Field(default=15, description="Display refresh interval in seconds")
    cycle_interval: int = Field(default=30, description="Seconds to show each plugin before cycling to next")

    # E-paper specific
    epaper_model: str = Field(default="epd2in13_V4", description="E-paper display model")
    epaper_rotation: int = Field(default=0, description="Display rotation (0, 90, 180, 270)")
    epaper_partial_refresh: bool = Field(default=True, description="Use partial refresh")
    epaper_clear_interval: int = Field(default=20, description="Full refresh every N updates")

    # Terminal specific
    terminal_width: int = Field(default=80, description="Terminal width")
    terminal_height: int = Field(default=24, description="Terminal height")
    terminal_colors: bool = Field(default=True, description="Use terminal colors")


class LayoutConfig(BaseModel):
    """Layout configuration."""
    type: LayoutType = Field(default=LayoutType.GRID)
    columns: int = Field(default=2, description="Number of columns (grid layout)")
    rows: int = Field(default=2, description="Number of rows (grid layout)")
    spacing: int = Field(default=5, description="Spacing between widgets")
    padding: int = Field(default=10, description="Padding around edges")

    # Widget placement
    widget_order: List[str] = Field(
        default=["clock", "weather", "currency", "crypto"],
        description="Order of widgets"
    )
    widget_sizes: Dict[str, Dict[str, int]] = Field(
        default={},
        description="Custom widget sizes {plugin: {width, height}}"
    )

    # Custom layout
    custom_layout: Optional[str] = Field(None, description="Path to custom layout file")


class PluginConfigs(BaseModel):
    """All plugin configurations."""
    weather: WeatherConfig = Field(default_factory=WeatherConfig)
    currency: CurrencyConfig = Field(default_factory=CurrencyConfig)
    crypto: CryptoConfig = Field(default_factory=CryptoConfig)
    stock: StockConfig = Field(default_factory=StockConfig)
    clock: ClockConfig = Field(default_factory=ClockConfig)

    # Custom plugins
    custom: Dict[str, Dict[str, Any]] = Field(
        default={},
        description="Configuration for custom plugins"
    )


class AppConfig(BaseModel):
    """Main application configuration."""
    app_name: str = Field(default="Raspi Info Ticker", description="Application name")
    version: str = Field(default="2.0.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Optional[str] = Field(None, description="Log file path")

    # Components
    auth: AuthConfig = Field(default_factory=AuthConfig)
    web_server: WebServerConfig = Field(default_factory=WebServerConfig)
    display: DisplayConfig = Field(default_factory=DisplayConfig)
    layout: LayoutConfig = Field(default_factory=LayoutConfig)
    plugins: PluginConfigs = Field(default_factory=PluginConfigs)

    # Data storage
    data_dir: str = Field(default="./data", description="Data directory")
    cache_dir: str = Field(default="./cache", description="Cache directory")
    plugin_dir: str = Field(default="./plugins", description="Custom plugins directory")

    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of {valid_levels}")
        return v.upper()

    class Config:
        env_prefix = "TICKER_"
        env_nested_delimiter = "__"


class WidgetConfig(BaseModel):
    """Configuration for individual widgets."""
    plugin: str = Field(..., description="Plugin name")
    position: Dict[str, int] = Field(..., description="Position {x, y}")
    size: Dict[str, int] = Field(..., description="Size {width, height}")
    style: Dict[str, Any] = Field(default={}, description="Custom styling")
    interactive: bool = Field(default=False, description="Enable interaction")
    auto_refresh: bool = Field(default=True, description="Auto-refresh widget")


class DashboardConfig(BaseModel):
    """Dashboard configuration."""
    name: str = Field(..., description="Dashboard name")
    description: Optional[str] = Field(None, description="Dashboard description")
    layout: LayoutConfig = Field(default_factory=LayoutConfig)
    widgets: List[WidgetConfig] = Field(default=[], description="Widget configurations")
    auto_cycle: bool = Field(default=False, description="Auto-cycle through screens")
    cycle_interval: int = Field(default=30, description="Cycle interval in seconds")


__all__ = [
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