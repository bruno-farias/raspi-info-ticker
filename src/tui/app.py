"""Main Textual TUI application for the info ticker."""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, Grid, ScrollableContainer
from textual.widgets import Header, Footer, Static, Button, Label, DataTable, Select, Input, Switch, TabbedContent, TabPane
from textual.reactive import reactive
from textual.message import Message
from textual.worker import Worker, WorkerState
from textual.binding import Binding
from rich.text import Text
from rich.table import Table
from rich.panel import Panel
from rich.console import Group
from rich.align import Align

from ..plugins import plugin_registry
from ..config import config_manager
from .widgets import PluginWidget, ConfigEditor, CitySelector, CurrencySelector


class PluginUpdate(Message):
    """Message sent when plugin data is updated."""
    def __init__(self, plugin_name: str, data: Dict[str, Any]):
        super().__init__()
        self.plugin_name = plugin_name
        self.data = data


class InfoTickerApp(App):
    """Main Textual application for info ticker."""

    CSS = """
    Screen {
        background: $surface;
    }

    #dashboard {
        layout: grid;
        grid-size: 2 2;
        grid-gutter: 1;
        padding: 1;
    }

    .plugin-widget {
        height: 100%;
        border: solid $primary;
        background: $panel;
        padding: 1;
    }

    #config-panel {
        dock: right;
        width: 40;
        border: solid $secondary;
        background: $panel;
        padding: 1;
    }

    #status-bar {
        dock: bottom;
        height: 3;
        border: solid $accent;
        background: $panel;
        padding: 0 1;
    }

    .config-section {
        margin: 1 0;
        padding: 1;
        border: solid $secondary;
    }

    .button-row {
        layout: horizontal;
        height: 3;
        margin: 1 0;
    }

    Button {
        margin: 0 1;
    }

    DataTable {
        height: 100%;
    }

    TabbedContent {
        height: 100%;
    }

    TabPane {
        padding: 1;
    }

    .error-message {
        color: $error;
        text-style: bold;
    }

    .success-message {
        color: $success;
        text-style: bold;
    }

    .warning-message {
        color: $warning;
        text-style: italic;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("d", "toggle_dashboard", "Dashboard"),
        Binding("c", "toggle_config", "Config"),
        Binding("r", "refresh_all", "Refresh All"),
        Binding("s", "save_config", "Save Config"),
        Binding("l", "load_config", "Load Config"),
        Binding("p", "toggle_plugins", "Plugins"),
        Binding("w", "cycle_weather", "Next Weather City"),
        Binding("e", "cycle_currency", "Next Currency"),
        Binding("t", "toggle_theme", "Toggle Theme"),
    ]

    def __init__(self):
        """Initialize the application."""
        super().__init__()
        self.logger = logging.getLogger("tui_app")
        self.plugin_widgets: Dict[str, PluginWidget] = {}
        self.update_workers: Dict[str, Worker] = {}
        self.config_loaded = False
        self.show_config = False
        self._theme_mode = "dark"

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header(show_clock=True)

        with Container(id="main-container"):
            # Main dashboard area
            with TabbedContent(initial="dashboard"):
                with TabPane("Dashboard", id="dashboard"):
                    yield from self._compose_dashboard()

                with TabPane("Plugins", id="plugins"):
                    yield from self._compose_plugins_tab()

                with TabPane("Configuration", id="configuration"):
                    yield from self._compose_config_tab()

                with TabPane("Layout", id="layout"):
                    yield from self._compose_layout_tab()

        # Status bar
        with Horizontal(id="status-bar"):
            yield Label("Status: Initializing...", id="status-label")
            yield Label("", id="update-time")

        yield Footer()

    def _compose_dashboard(self) -> ComposeResult:
        """Compose dashboard widgets."""
        # This will be populated dynamically based on loaded plugins
        yield Container(id="dashboard-container")

    def _compose_plugins_tab(self) -> ComposeResult:
        """Compose plugins management tab."""
        with Vertical():
            yield Label("Plugin Management", classes="title")
            yield DataTable(id="plugins-table")
            with Horizontal(classes="button-row"):
                yield Button("Enable", id="enable-plugin", variant="primary")
                yield Button("Disable", id="disable-plugin", variant="warning")
                yield Button("Configure", id="configure-plugin", variant="default")
                yield Button("Reload", id="reload-plugins", variant="success")

    def _compose_config_tab(self) -> ComposeResult:
        """Compose configuration tab."""
        with ScrollableContainer():
            yield Label("Application Configuration", classes="title")

            # Weather configuration
            with Vertical(classes="config-section"):
                yield Label("Weather Settings")
                yield CitySelector(id="city-selector")
                yield Button("Add City", id="add-city")
                yield Button("Remove City", id="remove-city")

            # Currency configuration
            with Vertical(classes="config-section"):
                yield Label("Currency Settings")
                yield CurrencySelector(id="currency-selector")
                yield Input(placeholder="Base Currency", id="base-currency")
                yield Button("Update Currencies", id="update-currencies")

            # Crypto configuration
            with Vertical(classes="config-section"):
                yield Label("Cryptocurrency Settings")
                yield Select(
                    options=[
                        ("bitcoin", "Bitcoin"),
                        ("ethereum", "Ethereum"),
                        ("cardano", "Cardano"),
                        ("polkadot", "Polkadot"),
                        ("chainlink", "Chainlink"),
                    ],
                    id="crypto-selector"
                )
                yield Label("Note: Select one crypto at a time", classes="warning-message")
                yield Button("Update Cryptos", id="update-cryptos")

            # Display settings
            with Vertical(classes="config-section"):
                yield Label("Display Settings")
                yield Input(placeholder="Refresh Interval (seconds)", id="refresh-interval", type="integer")
                with Horizontal():
                    yield Label("E-paper Mode:")
                    yield Switch(id="epaper-mode")
                with Horizontal():
                    yield Label("Terminal Colors:")
                    yield Switch(id="terminal-colors")

    def _compose_layout_tab(self) -> ComposeResult:
        """Compose layout configuration tab."""
        with Vertical():
            yield Label("Layout Designer", classes="title")
            yield Label("Drag and drop widgets to customize layout")
            yield Container(id="layout-designer")
            with Horizontal(classes="button-row"):
                yield Button("Save Layout", id="save-layout", variant="primary")
                yield Button("Reset Layout", id="reset-layout", variant="warning")
                yield Button("Load Template", id="load-template", variant="default")

    async def on_mount(self) -> None:
        """Initialize the application on mount."""
        self.logger.info("InfoTicker TUI starting...")

        # Load configuration
        await self.load_configuration()

        # Initialize plugins
        await self.initialize_plugins()

        # Start update workers
        await self.start_update_workers()

        # Update status
        self.query_one("#status-label").update("Status: Running")

    async def load_configuration(self) -> None:
        """Load application configuration."""
        try:
            config = config_manager.load(create_if_missing=True)
            self.config = config
            self.config_loaded = True
            self.logger.info("Configuration loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            self.notify("Failed to load configuration", severity="error")

    async def initialize_plugins(self) -> None:
        """Initialize and load plugins."""
        # Discover built-in plugins
        plugin_registry.discover_plugins()

        # Create plugin instances based on configuration
        if self.config_loaded:
            # Weather plugin
            if self.config.plugins.weather.enabled:
                weather_config = self.config.plugins.weather
                plugin_registry.create_plugin("weather", weather_config)

            # Currency plugin
            if self.config.plugins.currency.enabled:
                currency_config = self.config.plugins.currency
                plugin_registry.create_plugin("currency", currency_config)

            # Crypto plugin
            if self.config.plugins.crypto.enabled:
                crypto_config = self.config.plugins.crypto
                plugin_registry.create_plugin("crypto", crypto_config)

            # Clock plugin
            if self.config.plugins.clock.enabled:
                clock_config = self.config.plugins.clock
                plugin_registry.create_plugin("clock", clock_config)

        # Initialize all plugins
        await plugin_registry.initialize_all()

        # Create widgets for enabled plugins
        await self.create_plugin_widgets()

        # Update plugins table
        self.update_plugins_table()

    async def create_plugin_widgets(self) -> None:
        """Create widgets for all enabled plugins."""
        dashboard = self.query_one("#dashboard-container")
        dashboard.remove_children()

        # Create grid layout
        with dashboard:
            grid = Grid(id="plugin-grid")

            for plugin in plugin_registry.get_enabled_plugins():
                widget = PluginWidget(plugin.name, plugin.description)
                self.plugin_widgets[plugin.name] = widget
                grid.mount(widget)

    def update_plugins_table(self) -> None:
        """Update the plugins table with current plugin info."""
        table = self.query_one("#plugins-table", DataTable)
        table.clear(columns=True)

        # Add columns
        table.add_column("Name", key="name")
        table.add_column("Version", key="version")
        table.add_column("Status", key="status")
        table.add_column("Enabled", key="enabled")
        table.add_column("Description", key="description")

        # Add rows for each plugin
        for info in plugin_registry.get_plugin_info():
            status = "Active" if info["active"] else "Inactive"
            enabled = "Yes" if info["enabled"] else "No"
            table.add_row(
                info["name"],
                info["version"],
                status,
                enabled,
                info["description"],
                key=info["name"]
            )

    async def start_update_workers(self) -> None:
        """Start background workers to update plugin data."""
        for plugin in plugin_registry.get_enabled_plugins():
            worker = self.run_worker(self.update_plugin_data(plugin.name), exclusive=False)
            self.update_workers[plugin.name] = worker

    @work(exclusive=False)
    async def update_plugin_data(self, plugin_name: str) -> None:
        """Background worker to update plugin data."""
        plugin = plugin_registry.get_plugin(plugin_name)
        if not plugin:
            return

        while True:
            try:
                # Update plugin data
                data = await plugin.update()

                # Send update message
                self.post_message(PluginUpdate(plugin_name, data.dict()))

                # Update widget if it exists
                if plugin_name in self.plugin_widgets:
                    widget = self.plugin_widgets[plugin_name]
                    await widget.update_data(data.data)

                # Update status time
                self.query_one("#update-time").update(
                    f"Last update: {datetime.now().strftime('%H:%M:%S')}"
                )

            except Exception as e:
                self.logger.error(f"Error updating {plugin_name}: {e}")

            # Wait for update interval
            await asyncio.sleep(plugin.config.update_interval)

    async def on_plugin_update(self, message: PluginUpdate) -> None:
        """Handle plugin update messages."""
        plugin_name = message.plugin_name
        data = message.data

        # Update widget if it exists
        if plugin_name in self.plugin_widgets:
            widget = self.plugin_widgets[plugin_name]
            display_data = data.get("data", {})
            await widget.update_data(display_data)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id

        if button_id == "reload-plugins":
            await self.initialize_plugins()
            self.notify("Plugins reloaded")

        elif button_id == "save-layout":
            # TODO: Implement layout saving
            self.notify("Layout saved (not yet implemented)")

        elif button_id == "add-city":
            # TODO: Implement city addition dialog
            self.notify("Add city (not yet implemented)")

        elif button_id == "update-currencies":
            # TODO: Implement currency update
            self.notify("Currencies updated (not yet implemented)")

    async def action_quit(self) -> None:
        """Quit the application."""
        # Cleanup plugins
        await plugin_registry.cleanup_all()

        # Save configuration if changed
        if self.config_loaded:
            config_manager.save()

        # Exit
        self.exit()

    async def action_toggle_dashboard(self) -> None:
        """Toggle dashboard view."""
        tabbed_content = self.query_one(TabbedContent)
        tabbed_content.active = "dashboard"

    async def action_toggle_config(self) -> None:
        """Toggle configuration view."""
        tabbed_content = self.query_one(TabbedContent)
        tabbed_content.active = "configuration"

    async def action_refresh_all(self) -> None:
        """Force refresh all plugins."""
        for plugin in plugin_registry.get_enabled_plugins():
            data = await plugin.update(force=True)
            if plugin.name in self.plugin_widgets:
                widget = self.plugin_widgets[plugin.name]
                await widget.update_data(data.data)
        self.notify("All plugins refreshed")

    async def action_save_config(self) -> None:
        """Save current configuration."""
        if self.config_loaded:
            config_manager.save()
            self.notify("Configuration saved")

    async def action_load_config(self) -> None:
        """Reload configuration from file."""
        await self.load_configuration()
        await self.initialize_plugins()
        self.notify("Configuration reloaded")

    async def action_toggle_plugins(self) -> None:
        """Toggle plugins view."""
        tabbed_content = self.query_one(TabbedContent)
        tabbed_content.active = "plugins"

    async def action_cycle_weather(self) -> None:
        """Cycle to next weather city."""
        weather_plugin = plugin_registry.get_plugin("weather")
        if weather_plugin and weather_plugin.supports_interaction():
            await weather_plugin.handle_interaction("next_city", {})
            await weather_plugin.update(force=True)
            self.notify("Weather city changed")

    async def action_cycle_currency(self) -> None:
        """Cycle currency display."""
        # TODO: Implement currency cycling
        self.notify("Currency cycling (not yet implemented)")

    async def action_toggle_theme(self) -> None:
        """Toggle between light and dark theme."""
        if self._theme_mode == "dark":
            self.theme = "textual-light"
            self._theme_mode = "light"
        else:
            self.theme = "textual-dark"
            self._theme_mode = "dark"
        self.notify(f"Theme changed to {self._theme_mode}")


def run_app():
    """Run the Textual application."""
    app = InfoTickerApp()
    app.run()


if __name__ == "__main__":
    run_app()