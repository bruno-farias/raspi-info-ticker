"""Tests for plugin system."""

import pytest
from typing import Dict, Any
from pydantic import BaseModel, Field

from src.plugins import PluginRegistry, BasePlugin, PluginConfig, PluginData


class MockPluginConfig(PluginConfig):
    """Mock plugin configuration for testing."""
    test_value: str = "default"


class MockPlugin(BasePlugin):
    """Test plugin implementation."""

    name = "test"
    version = "1.0.0"
    description = "Test Plugin"
    author = "Test"

    def __init__(self, config: MockPluginConfig = None):
        super().__init__(config or MockPluginConfig())

    def get_config_schema(self):
        return MockPluginConfig

    async def fetch_data(self) -> Dict[str, Any]:
        return {"test": "data", "value": self.config.test_value}

    def get_display_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {"formatted": data.get("test", "none")}


class TestPluginRegistry:
    """Test PluginRegistry."""

    def test_register_plugin_class(self, fresh_plugin_registry):
        """Test registering a plugin class."""
        registry = fresh_plugin_registry
        initial_count = len(registry.plugin_classes)

        registry.register_plugin_class(MockPlugin)

        assert "test" in registry.plugin_classes
        assert registry.plugin_classes["test"] == MockPlugin
        assert len(registry.plugin_classes) == initial_count + 1

    def test_create_plugin(self, fresh_plugin_registry):
        """Test creating a plugin instance."""
        registry = fresh_plugin_registry
        registry.register_plugin_class(MockPlugin)

        config = MockPluginConfig(enabled=True, test_value="custom")
        plugin = registry.create_plugin("test", config)

        assert plugin is not None
        assert isinstance(plugin, MockPlugin)
        assert plugin.config.test_value == "custom"
        assert "test" in registry.plugins

    def test_create_multiple_instances(self, fresh_plugin_registry):
        """Test creating multiple instances of same plugin."""
        registry = fresh_plugin_registry
        registry.register_plugin_class(MockPlugin)

        # Create first instance
        plugin1 = registry.create_plugin("test", MockPluginConfig())
        assert "test" in registry.plugins

        # Create second instance with explicit ID
        plugin2 = registry.create_plugin("test", MockPluginConfig(), instance_id="test_2")
        assert "test_2" in registry.plugins

        # Both should be different instances
        assert plugin1 is not plugin2
        assert len(registry.plugins) == 2

    def test_get_plugin(self, fresh_plugin_registry):
        """Test retrieving a plugin."""
        registry = fresh_plugin_registry
        registry.register_plugin_class(MockPlugin)
        registry.create_plugin("test")

        plugin = registry.get_plugin("test")
        assert plugin is not None
        assert isinstance(plugin, MockPlugin)

    def test_get_nonexistent_plugin(self, fresh_plugin_registry):
        """Test retrieving non-existent plugin."""
        registry = fresh_plugin_registry
        plugin = registry.get_plugin("nonexistent")
        assert plugin is None

    def test_get_enabled_plugins(self, fresh_plugin_registry):
        """Test getting only enabled plugins."""
        registry = fresh_plugin_registry
        registry.register_plugin_class(MockPlugin)

        # Create enabled plugin
        enabled_config = MockPluginConfig(enabled=True)
        registry.create_plugin("test", enabled_config, instance_id="test_enabled")

        # Create disabled plugin
        disabled_config = MockPluginConfig(enabled=False)
        registry.create_plugin("test", disabled_config, instance_id="test_disabled")

        enabled = registry.get_enabled_plugins()
        assert len(enabled) == 1
        assert enabled[0].config.enabled is True


class TestBasePlugin:
    """Test BasePlugin."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test plugin initialization."""
        plugin = MockPlugin()
        await plugin.initialize()
        # Should not raise any errors

    @pytest.mark.asyncio
    async def test_update(self):
        """Test plugin update."""
        plugin = MockPlugin(MockPluginConfig(enabled=True))
        result = await plugin.update()

        assert isinstance(result, PluginData)
        assert result.plugin_name == "test"
        assert result.metadata["raw_data"]["test"] == "data"
        assert result.data["formatted"] == "data"

    @pytest.mark.asyncio
    async def test_update_disabled_plugin(self):
        """Test updating disabled plugin."""
        plugin = MockPlugin(MockPluginConfig(enabled=False))
        result = await plugin.update()

        assert result.error is not None
        assert "disabled" in result.error.lower()

    @pytest.mark.asyncio
    async def test_update_with_cache(self):
        """Test plugin caching."""
        config = MockPluginConfig(enabled=True, cache_ttl=10)
        plugin = MockPlugin(config)

        # First update - should fetch
        result1 = await plugin.update()
        assert result1.metadata.get("from_cache", False) is False

        # Second update - should use cache
        result2 = await plugin.update()
        assert result2.metadata.get("from_cache", False) is True
        assert result2.metadata["raw_data"] == result1.metadata["raw_data"]

    @pytest.mark.asyncio
    async def test_update_force_refresh(self):
        """Test forcing cache refresh."""
        config = MockPluginConfig(enabled=True, cache_ttl=10)
        plugin = MockPlugin(config)

        # First update
        await plugin.update()

        # Force refresh
        result = await plugin.update(force=True)
        assert result.metadata.get("from_cache", False) is False

    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Test plugin cleanup."""
        plugin = MockPlugin()
        await plugin.cleanup()
        # Should not raise any errors


class TestPluginData:
    """Test PluginData."""

    def test_plugin_data_creation(self):
        """Test creating PluginData."""
        data = PluginData(
            plugin_name="test",
            title="Test Plugin",
            data={"formatted": "value"},
            metadata={"raw_data": {"key": "value"}}
        )

        assert data.plugin_name == "test"
        assert data.title == "Test Plugin"
        assert data.metadata["raw_data"]["key"] == "value"
        assert data.data["formatted"] == "value"
        assert data.error is None

    def test_plugin_data_with_error(self):
        """Test PluginData with error."""
        data = PluginData(
            plugin_name="test",
            title="Test Plugin",
            data={},
            error="Test error"
        )

        assert data.error == "Test error"
        assert data.data == {}
