"""Configuration manager for the info ticker system."""

import os
import yaml
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Union
from pydantic import ValidationError

from .schemas import AppConfig, PluginConfigs


class ConfigManager:
    """Manages application configuration."""

    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """
        Initialize configuration manager.

        Args:
            config_path: Path to configuration file
        """
        self.logger = logging.getLogger("config_manager")
        self.config_path = Path(config_path) if config_path else self._find_config_file()
        self.config: Optional[AppConfig] = None
        self._watchers = []

    def _find_config_file(self) -> Path:
        """Find configuration file in standard locations."""
        search_paths = [
            Path.cwd() / "config.yaml",
            Path.cwd() / "config.yml",
            Path.cwd() / "config.json",
            Path.cwd() / "config" / "config.yaml",
            Path.cwd() / "config" / "config.yml",
            Path.home() / ".raspi-info-ticker" / "config.yaml",
            Path("/etc/raspi-info-ticker/config.yaml"),
        ]

        for path in search_paths:
            if path.exists():
                self.logger.info(f"Found config file: {path}")
                return path

        # Default to config.yaml in current directory
        default_path = Path.cwd() / "config" / "config.yaml"
        self.logger.warning(f"No config file found, will use default: {default_path}")
        return default_path

    def load(self, create_if_missing: bool = True) -> AppConfig:
        """
        Load configuration from file.

        Args:
            create_if_missing: Create default config if file doesn't exist

        Returns:
            Loaded configuration

        Raises:
            ValidationError: If configuration is invalid
        """
        if not self.config_path.exists():
            if create_if_missing:
                self.logger.info("Creating default configuration")
                self.config = self.create_default_config()
                self.save()
            else:
                raise FileNotFoundError(f"Config file not found: {self.config_path}")
        else:
            self.logger.info(f"Loading config from {self.config_path}")
            try:
                # Load from file
                with open(self.config_path, 'r') as f:
                    if self.config_path.suffix in ['.yaml', '.yml']:
                        data = yaml.safe_load(f)
                    elif self.config_path.suffix == '.json':
                        data = json.load(f)
                    else:
                        raise ValueError(f"Unsupported config format: {self.config_path.suffix}")

                # Load environment variables (override file config)
                data = self._merge_env_vars(data)

                # Validate and create config
                self.config = AppConfig(**data) if data else AppConfig()

            except ValidationError as e:
                self.logger.error(f"Configuration validation failed: {e}")
                raise
            except Exception as e:
                self.logger.error(f"Failed to load configuration: {e}")
                raise

        return self.config

    def save(self, path: Optional[Path] = None) -> None:
        """
        Save configuration to file.

        Args:
            path: Path to save to (default: current config path)
        """
        save_path = path or self.config_path
        save_path.parent.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Saving config to {save_path}")

        # Convert to dictionary
        data = self.config.dict(exclude_unset=False)

        # Save based on file extension
        with open(save_path, 'w') as f:
            if save_path.suffix in ['.yaml', '.yml']:
                yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
            elif save_path.suffix == '.json':
                json.dump(data, f, indent=2)
            else:
                raise ValueError(f"Unsupported config format: {save_path.suffix}")

    def create_default_config(self) -> AppConfig:
        """
        Create default configuration.

        Returns:
            Default configuration
        """
        # Try to migrate from old .env file if it exists
        env_data = self._migrate_from_env()

        # Create default config with migrated data
        config = AppConfig()

        # Apply migrated settings
        if env_data:
            self.logger.info("Migrating settings from .env file")

            # Currency API
            if "FREE_CURRENCY_API_KEY" in env_data:
                config.plugins.currency.api_key = env_data["FREE_CURRENCY_API_KEY"]

            # Crypto API
            if "CRYPTO_API_KEY" in env_data:
                config.plugins.crypto.api_key = env_data["CRYPTO_API_KEY"]
            if "CRYPTO_API_SOURCE" in env_data:
                config.plugins.crypto.provider = env_data["CRYPTO_API_SOURCE"]

            # Weather API
            if "OPEN_WEATHER_API_KEY" in env_data:
                config.plugins.weather.api_key = env_data["OPEN_WEATHER_API_KEY"]
            if "OPEN_WEATHER_CITY" in env_data:
                city = {"name": env_data["OPEN_WEATHER_CITY"]}
                if "OPEN_WEATHER_STATE" in env_data:
                    city["state"] = env_data["OPEN_WEATHER_STATE"]
                if "OPEN_WEATHER_COUNTRY" in env_data:
                    city["country"] = env_data["OPEN_WEATHER_COUNTRY"]
                config.plugins.weather.cities = [city]

            # Display settings
            if "REFRESH_INTERVAL" in env_data:
                config.display.refresh_interval = int(env_data["REFRESH_INTERVAL"])

            # Screen order
            if "SCREEN_ORDER" in env_data:
                order = env_data["SCREEN_ORDER"].split(",")
                config.layout.widget_order = [s.strip() for s in order]

            # Generate a secret key for auth if not present
            if not config.auth.secret_key:
                import secrets
                config.auth.secret_key = secrets.token_urlsafe(32)

        return config

    def _migrate_from_env(self) -> Dict[str, str]:
        """
        Migrate settings from old .env file.

        Returns:
            Dictionary of environment variables
        """
        env_data = {}
        env_path = Path.cwd() / ".env"

        if env_path.exists():
            try:
                from dotenv import dotenv_values
                env_data = dotenv_values(env_path)
                self.logger.info(f"Found .env file with {len(env_data)} settings")
            except Exception as e:
                self.logger.warning(f"Failed to load .env file: {e}")

        # Also check actual environment variables
        env_vars = [
            "FREE_CURRENCY_API_KEY",
            "CRYPTO_API_KEY",
            "CRYPTO_API_SOURCE",
            "OPEN_WEATHER_API_KEY",
            "OPEN_WEATHER_CITY",
            "OPEN_WEATHER_STATE",
            "OPEN_WEATHER_COUNTRY",
            "REFRESH_INTERVAL",
            "SCREEN_ORDER",
            "CACHE_DEFAULT_TTL",
            "CACHE_PER_SCREEN"
        ]

        for var in env_vars:
            value = os.getenv(var)
            if value and var not in env_data:
                env_data[var] = value

        return env_data

    def _merge_env_vars(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge environment variables into configuration.

        Args:
            data: Base configuration data

        Returns:
            Merged configuration
        """
        # Check for environment variables with TICKER_ prefix
        prefix = "TICKER_"
        delimiter = "__"

        for key, value in os.environ.items():
            if not key.startswith(prefix):
                continue

            # Remove prefix and convert to nested path
            path = key[len(prefix):].lower().split(delimiter)

            # Navigate to the correct position in data
            current = data
            for part in path[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]

            # Set the value
            current[path[-1]] = value

        return data

    def update(self, updates: Dict[str, Any]) -> None:
        """
        Update configuration with new values.

        Args:
            updates: Dictionary of updates to apply
        """
        if not self.config:
            raise ValueError("Configuration not loaded")

        # Merge updates into current config
        current_data = self.config.dict()
        merged_data = self._deep_merge(current_data, updates)

        # Validate and update
        self.config = AppConfig(**merged_data)
        self.logger.info("Configuration updated")

    def _deep_merge(self, base: Dict, updates: Dict) -> Dict:
        """
        Deep merge two dictionaries.

        Args:
            base: Base dictionary
            updates: Updates to apply

        Returns:
            Merged dictionary
        """
        result = base.copy()

        for key, value in updates.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def get_plugin_config(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Plugin configuration or None
        """
        if not self.config:
            return None

        # Check built-in plugins
        if hasattr(self.config.plugins, plugin_name):
            return getattr(self.config.plugins, plugin_name).dict()

        # Check custom plugins
        return self.config.plugins.custom.get(plugin_name)

    def set_plugin_config(self, plugin_name: str, config: Dict[str, Any]) -> None:
        """
        Set configuration for a specific plugin.

        Args:
            plugin_name: Name of the plugin
            config: Plugin configuration
        """
        if not self.config:
            raise ValueError("Configuration not loaded")

        # Check if it's a built-in plugin
        if hasattr(self.config.plugins, plugin_name):
            plugin_class = type(getattr(self.config.plugins, plugin_name))
            setattr(self.config.plugins, plugin_name, plugin_class(**config))
        else:
            # Custom plugin
            self.config.plugins.custom[plugin_name] = config

        self.logger.info(f"Updated config for plugin: {plugin_name}")

    def validate(self) -> bool:
        """
        Validate current configuration.

        Returns:
            True if valid, False otherwise
        """
        try:
            if self.config:
                AppConfig(**self.config.dict())
                return True
            return False
        except ValidationError as e:
            self.logger.error(f"Configuration validation failed: {e}")
            return False

    def export_env(self, path: Optional[Path] = None) -> None:
        """
        Export configuration as environment variables.

        Args:
            path: Path to save .env file
        """
        if not self.config:
            raise ValueError("Configuration not loaded")

        env_path = path or Path.cwd() / ".env.generated"
        self.logger.info(f"Exporting config to {env_path}")

        lines = []
        lines.append("# Generated from config.yaml")
        lines.append("")

        # Export key settings
        if self.config.plugins.currency.api_key:
            lines.append(f"FREE_CURRENCY_API_KEY={self.config.plugins.currency.api_key}")

        if self.config.plugins.crypto.api_key:
            lines.append(f"CRYPTO_API_KEY={self.config.plugins.crypto.api_key}")

        if self.config.plugins.weather.api_key:
            lines.append(f"OPEN_WEATHER_API_KEY={self.config.plugins.weather.api_key}")

        if self.config.plugins.weather.cities:
            city = self.config.plugins.weather.cities[0]
            lines.append(f"OPEN_WEATHER_CITY={city.get('name', '')}")
            if 'state' in city:
                lines.append(f"OPEN_WEATHER_STATE={city['state']}")
            if 'country' in city:
                lines.append(f"OPEN_WEATHER_COUNTRY={city['country']}")

        lines.append(f"REFRESH_INTERVAL={self.config.display.refresh_interval}")
        lines.append(f"SCREEN_ORDER={','.join(self.config.layout.widget_order)}")

        # Write to file
        with open(env_path, 'w') as f:
            f.write('\n'.join(lines))


# Global config manager instance
config_manager = ConfigManager()


__all__ = ["ConfigManager", "config_manager"]