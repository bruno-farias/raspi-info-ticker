"""Plugin system for the info ticker."""

from typing import Dict, List, Optional, Type
import logging
import importlib
import inspect
from pathlib import Path

from .base import BasePlugin, PluginConfig, PluginData


class PluginRegistry:
    """Central registry for managing plugins."""

    def __init__(self):
        """Initialize the plugin registry."""
        self.plugins: Dict[str, BasePlugin] = {}  # instance_id -> plugin
        self.plugin_classes: Dict[str, Type[BasePlugin]] = {}  # plugin_type -> class
        self.logger = logging.getLogger("plugin_registry")
        self._instance_counter: Dict[str, int] = {}  # plugin_type -> count

    def register_plugin_class(self, plugin_class: Type[BasePlugin]) -> None:
        """
        Register a plugin class.

        Args:
            plugin_class: Plugin class to register
        """
        if not issubclass(plugin_class, BasePlugin):
            raise ValueError(f"{plugin_class} must inherit from BasePlugin")

        name = plugin_class.name
        if name in self.plugin_classes:
            self.logger.warning(f"Plugin class {name} already registered, overwriting")

        self.plugin_classes[name] = plugin_class
        self.logger.info(f"Registered plugin class: {name}")

    def create_plugin(self, plugin_type: str, config: Optional[PluginConfig] = None, instance_id: Optional[str] = None) -> BasePlugin:
        """
        Create a plugin instance.

        Args:
            plugin_type: Plugin type/class name (e.g., "weather")
            config: Plugin configuration
            instance_id: Optional unique ID for this instance (auto-generated if None)

        Returns:
            Plugin instance

        Raises:
            KeyError: If plugin type not found
        """
        if plugin_type not in self.plugin_classes:
            raise KeyError(f"Plugin type {plugin_type} not found in registry")

        # Generate unique instance ID if not provided
        if instance_id is None:
            count = self._instance_counter.get(plugin_type, 0)
            self._instance_counter[plugin_type] = count + 1
            instance_id = f"{plugin_type}_{count}" if count > 0 else plugin_type

        # Create plugin instance
        plugin_class = self.plugin_classes[plugin_type]
        plugin = plugin_class(config)

        # Store with unique instance ID
        self.plugins[instance_id] = plugin
        self.logger.info(f"Created plugin instance: {instance_id} (type: {plugin_type})")

        return plugin

    def get_plugin(self, name: str) -> Optional[BasePlugin]:
        """
        Get an active plugin instance.

        Args:
            name: Plugin name

        Returns:
            Plugin instance or None if not found
        """
        return self.plugins.get(name)

    def get_all_plugins(self) -> List[BasePlugin]:
        """Get all active plugin instances."""
        return list(self.plugins.values())

    def get_enabled_plugins(self) -> List[BasePlugin]:
        """Get all enabled plugin instances."""
        return [p for p in self.plugins.values() if p.config.enabled]

    def discover_plugins(self, plugin_dir: Optional[Path] = None) -> None:
        """
        Discover and load plugins from a directory.

        Args:
            plugin_dir: Directory to search for plugins (default: current package)
        """
        if plugin_dir is None:
            plugin_dir = Path(__file__).parent

        self.logger.info(f"Discovering plugins in {plugin_dir}")

        for file_path in plugin_dir.glob("*.py"):
            if file_path.name.startswith("_") or file_path.name == "base.py":
                continue

            module_name = file_path.stem
            try:
                # Import the module
                if plugin_dir == Path(__file__).parent:
                    # Built-in plugins
                    module = importlib.import_module(f".{module_name}", package="src.plugins")
                else:
                    # External plugins
                    spec = importlib.util.spec_from_file_location(module_name, file_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                # Find plugin classes
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and
                        issubclass(obj, BasePlugin) and
                        obj != BasePlugin and
                        hasattr(obj, 'name')):
                        self.register_plugin_class(obj)

            except Exception as e:
                self.logger.error(f"Failed to load plugin from {file_path}: {e}")

    async def initialize_all(self) -> None:
        """Initialize all plugin instances."""
        for plugin in self.plugins.values():
            try:
                await plugin.initialize()
            except Exception as e:
                self.logger.error(f"Failed to initialize {plugin.name}: {e}")

    async def cleanup_all(self) -> None:
        """Cleanup all plugin instances."""
        for plugin in self.plugins.values():
            try:
                await plugin.cleanup()
            except Exception as e:
                self.logger.error(f"Failed to cleanup {plugin.name}: {e}")

    def get_plugin_info(self) -> List[Dict]:
        """
        Get information about all registered plugins.

        Returns:
            List of plugin information dictionaries
        """
        info = []
        for name, plugin_class in self.plugin_classes.items():
            plugin = self.plugins.get(name)
            info.append({
                "name": name,
                "version": plugin_class.version,
                "description": plugin_class.description,
                "author": plugin_class.author,
                "active": plugin is not None,
                "enabled": plugin.config.enabled if plugin else False
            })
        return info


# Global plugin registry instance
plugin_registry = PluginRegistry()


__all__ = [
    "BasePlugin",
    "PluginConfig",
    "PluginData",
    "PluginRegistry",
    "plugin_registry"
]