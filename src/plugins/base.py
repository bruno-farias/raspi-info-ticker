"""Base plugin class for the info ticker system."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
import asyncio
import logging


class PluginConfig(BaseModel):
    """Base configuration for all plugins."""
    enabled: bool = Field(default=True, description="Whether the plugin is enabled")
    update_interval: int = Field(default=60, description="Update interval in seconds")
    cache_ttl: int = Field(default=300, description="Cache TTL in seconds")
    priority: int = Field(default=0, description="Display priority (higher = more important)")

    class Config:
        extra = "allow"  # Allow additional fields for plugin-specific config


class PluginData(BaseModel):
    """Standard data format returned by plugins."""
    plugin_name: str
    title: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BasePlugin(ABC):
    """Abstract base class for all plugins."""

    # Plugin metadata (should be overridden in subclasses)
    name: str = "base_plugin"
    version: str = "1.0.0"
    description: str = "Base plugin"
    author: str = "Unknown"

    def __init__(self, config: Optional[PluginConfig] = None):
        """Initialize the plugin with configuration."""
        self.config = config or PluginConfig()
        self.logger = logging.getLogger(f"plugin.{self.name}")
        self._last_data: Optional[PluginData] = None
        self._last_update: Optional[datetime] = None
        self._update_lock = asyncio.Lock()

    @abstractmethod
    async def fetch_data(self) -> Dict[str, Any]:
        """
        Fetch data from the plugin's data source.

        Returns:
            Dict containing the fetched data

        Raises:
            Exception: If data fetching fails
        """
        pass

    @abstractmethod
    def get_display_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format data for display.

        Args:
            data: Raw data from fetch_data()

        Returns:
            Formatted data ready for display
        """
        pass

    @abstractmethod
    def get_config_schema(self) -> type[BaseModel]:
        """
        Get the Pydantic model for plugin-specific configuration.

        Returns:
            Pydantic model class for configuration
        """
        pass

    async def update(self, force: bool = False) -> PluginData:
        """
        Update plugin data with caching support.

        Args:
            force: Force update even if cache is valid

        Returns:
            PluginData object with latest information
        """
        async with self._update_lock:
            # Check cache validity
            if not force and self._is_cache_valid():
                self.logger.debug(f"{self.name}: Using cached data")
                return self._last_data

            try:
                # Fetch fresh data
                self.logger.info(f"{self.name}: Fetching fresh data")
                raw_data = await self.fetch_data()
                display_data = self.get_display_data(raw_data)

                # Create plugin data object
                plugin_data = PluginData(
                    plugin_name=self.name,
                    title=self.get_title(),
                    data=display_data,
                    metadata={
                        "raw_data": raw_data,
                        "version": self.version,
                        "priority": self.config.priority
                    }
                )

                # Update cache
                self._last_data = plugin_data
                self._last_update = datetime.now()

                return plugin_data

            except Exception as e:
                self.logger.error(f"{self.name}: Error fetching data - {e}")

                # Return error data
                return PluginData(
                    plugin_name=self.name,
                    title=self.get_title(),
                    data={},
                    error=str(e)
                )

    def _is_cache_valid(self) -> bool:
        """Check if cached data is still valid."""
        if not self._last_data or not self._last_update:
            return False

        age = (datetime.now() - self._last_update).total_seconds()
        return age < self.config.cache_ttl

    def get_title(self) -> str:
        """Get display title for the plugin."""
        return self.description

    async def initialize(self) -> None:
        """
        Initialize plugin resources.
        Override in subclasses if needed.
        """
        self.logger.info(f"{self.name}: Initialized")

    async def cleanup(self) -> None:
        """
        Cleanup plugin resources.
        Override in subclasses if needed.
        """
        self.logger.info(f"{self.name}: Cleaned up")

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate plugin configuration.

        Args:
            config: Configuration dictionary

        Returns:
            True if configuration is valid
        """
        try:
            schema = self.get_config_schema()
            schema(**config)
            return True
        except Exception as e:
            self.logger.error(f"{self.name}: Config validation failed - {e}")
            return False

    def get_widget_layout(self) -> Dict[str, Any]:
        """
        Get the preferred widget layout for this plugin.
        Override in subclasses to customize display.

        Returns:
            Dictionary describing widget layout preferences
        """
        return {
            "type": "default",
            "min_width": 20,
            "min_height": 3,
            "expandable": True
        }

    def supports_interaction(self) -> bool:
        """Check if plugin supports user interaction."""
        return False

    async def handle_interaction(self, action: str, params: Dict[str, Any]) -> Any:
        """
        Handle user interaction.
        Override in interactive plugins.

        Args:
            action: Action to perform
            params: Action parameters

        Returns:
            Result of the action
        """
        raise NotImplementedError(f"{self.name} does not support interaction")