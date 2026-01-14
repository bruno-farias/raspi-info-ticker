"""Custom widgets for the Textual TUI application."""

from typing import Dict, Any, List, Optional
from datetime import datetime

from textual.app import ComposeResult
from textual.widgets import Static, Button, Input, Select, DataTable, Label
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.reactive import reactive
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich.align import Align
from rich.console import RenderableType


class PluginWidget(Static):
    """Widget to display plugin data."""

    def __init__(self, plugin_name: str, title: str = "", **kwargs):
        """Initialize plugin widget."""
        super().__init__(**kwargs)
        self.plugin_name = plugin_name
        self.title = title or plugin_name.title()
        self.data = {}
        self.classes = "plugin-widget"

    async def update_data(self, data: Dict[str, Any]) -> None:
        """Update widget with new data."""
        self.data = data
        self.refresh()

    def render(self) -> RenderableType:
        """Render the plugin widget."""
        if not self.data:
            content = Text("No data available", style="dim italic")
        else:
            content = self._render_plugin_data()

        return Panel(
            content,
            title=f"[bold]{self.title}[/bold]",
            border_style="blue",
            padding=(1, 2)
        )

    def _render_plugin_data(self) -> RenderableType:
        """Render plugin-specific data."""
        # Clock plugin
        if self.plugin_name == "clock":
            return self._render_clock_data()

        # Weather plugin
        elif self.plugin_name == "weather":
            return self._render_weather_data()

        # Currency plugin
        elif self.plugin_name == "currency":
            return self._render_currency_data()

        # Crypto plugin
        elif self.plugin_name == "crypto":
            return self._render_crypto_data()

        # Default rendering
        else:
            return self._render_default_data()

    def _render_clock_data(self) -> RenderableType:
        """Render clock data."""
        lines = self.data.get("formatted_lines", [])
        if lines:
            text = Text()
            # Large time display
            if lines:
                text.append(lines[0], style="bold cyan", justify="center")
            # Date and other info
            for line in lines[1:]:
                text.append("\n" + line, style="yellow", justify="center")
            return Align.center(text, vertical="middle")
        return Text("No time data", style="dim")

    def _render_weather_data(self) -> RenderableType:
        """Render weather data."""
        if "error" in self.data:
            return Text(f"Error: {self.data['error']}", style="red")

        text = Text()

        # City and temperature
        city = self.data.get("city", "Unknown")
        country = self.data.get("country", "")
        temp = self.data.get("temperature", 0)
        feels_like = self.data.get("feels_like", 0)
        units = "°C" if self.data.get("units") == "metric" else "°F"

        location = f"{city}, {country}" if country else city
        text.append(f"{location}\n", style="bold cyan")
        text.append(f"{temp}{units} ", style="bold yellow")
        text.append(f"(feels like {feels_like}{units})\n", style="dim")

        # Weather description
        description = self.data.get("description", "")
        if description:
            text.append(f"{description}\n", style="white")

        # Additional details
        humidity = self.data.get("humidity", 0)
        wind_speed = self.data.get("wind_speed", 0)
        text.append(f"\nHumidity: {humidity}%  Wind: {wind_speed} m/s", style="dim")

        # Min/Max temperatures
        temp_min = self.data.get("temp_min", 0)
        temp_max = self.data.get("temp_max", 0)
        text.append(f"\nMin: {temp_min}{units}  Max: {temp_max}{units}", style="dim")

        return text

    def _render_currency_data(self) -> RenderableType:
        """Render currency data."""
        if "error" in self.data:
            return Text(f"Error: {self.data['error']}", style="red")

        table = Table(show_header=True, header_style="bold cyan", box=None)
        table.add_column("Pair", style="white")
        table.add_column("Rate", style="yellow")
        table.add_column("Change", style="green")

        pairs = self.data.get("pairs", [])
        for pair_data in pairs:
            pair = pair_data.get("pair", "")
            rate = pair_data.get("rate", 0)
            change = pair_data.get("change_indicator", "")

            # Color code the change
            if "↑" in change:
                change_style = "green"
            elif "↓" in change:
                change_style = "red"
            else:
                change_style = "dim"

            table.add_row(
                pair,
                f"{rate:.4f}",
                Text(change, style=change_style) if change else ""
            )

        return table

    def _render_crypto_data(self) -> RenderableType:
        """Render cryptocurrency data."""
        if "error" in self.data:
            return Text(f"Error: {self.data['error']}", style="red")

        table = Table(show_header=True, header_style="bold cyan", box=None)
        table.add_column("Coin", style="white")
        table.add_column("Price", style="yellow")
        table.add_column("24h", style="green")

        coins = self.data.get("coins", [])
        for coin_data in coins:
            name = coin_data.get("name", "")
            symbol = coin_data.get("symbol", "")
            prices = coin_data.get("prices", {})

            # Get USD price (or first available)
            price_data = prices.get("USD", {}) if "USD" in prices else next(iter(prices.values()), {})
            price = price_data.get("formatted", "N/A")
            change = price_data.get("change_24h_formatted", "")

            # Color code the change
            if "↑" in change:
                change_style = "green"
            elif "↓" in change:
                change_style = "red"
            else:
                change_style = "dim"

            table.add_row(
                f"{name} ({symbol})",
                price,
                Text(change, style=change_style) if change else ""
            )

        return table

    def _render_default_data(self) -> RenderableType:
        """Default rendering for unknown plugins."""
        text = Text()
        for key, value in self.data.items():
            if not key.startswith("_"):
                text.append(f"{key}: {value}\n")
        return text


class ConfigEditor(Container):
    """Widget for editing configuration."""

    def __init__(self, config_data: Dict[str, Any], **kwargs):
        """Initialize config editor."""
        super().__init__(**kwargs)
        self.config_data = config_data
        self.inputs = {}

    def compose(self) -> ComposeResult:
        """Compose the config editor."""
        with ScrollableContainer():
            yield from self._create_config_fields(self.config_data)

    def _create_config_fields(self, data: Dict[str, Any], prefix: str = "") -> ComposeResult:
        """Recursively create configuration fields."""
        for key, value in data.items():
            field_id = f"{prefix}{key}" if prefix else key

            if isinstance(value, dict):
                # Nested configuration
                yield Label(f"{key.replace('_', ' ').title()}:", classes="config-label")
                yield from self._create_config_fields(value, f"{field_id}.")
            elif isinstance(value, bool):
                # Boolean field - use switch
                from textual.widgets import Switch
                switch = Switch(value=value, id=field_id)
                self.inputs[field_id] = switch
                yield Horizontal(
                    Label(f"{key.replace('_', ' ').title()}:"),
                    switch
                )
            elif isinstance(value, (int, float)):
                # Numeric field
                input_field = Input(
                    value=str(value),
                    placeholder=key.replace('_', ' ').title(),
                    id=field_id,
                    type="number"
                )
                self.inputs[field_id] = input_field
                yield input_field
            elif isinstance(value, list):
                # List field - use text area or multiple selects
                if value and isinstance(value[0], str):
                    input_field = Input(
                        value=", ".join(value),
                        placeholder=key.replace('_', ' ').title(),
                        id=field_id
                    )
                    self.inputs[field_id] = input_field
                    yield input_field
                else:
                    yield Label(f"{key}: [complex list]")
            else:
                # String field
                input_field = Input(
                    value=str(value) if value else "",
                    placeholder=key.replace('_', ' ').title(),
                    id=field_id
                )
                self.inputs[field_id] = input_field
                yield input_field

    def get_config(self) -> Dict[str, Any]:
        """Get the edited configuration."""
        result = {}
        for field_id, widget in self.inputs.items():
            keys = field_id.split(".")
            current = result

            # Navigate to the correct nested position
            for key in keys[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]

            # Get the value from the widget
            if isinstance(widget, Input):
                value = widget.value
                # Try to convert to appropriate type
                if widget.type == "number":
                    try:
                        value = float(value) if "." in value else int(value)
                    except ValueError:
                        pass
                elif "," in value:
                    # Assume it's a list
                    value = [v.strip() for v in value.split(",")]
            elif hasattr(widget, "value"):
                value = widget.value
            else:
                value = None

            # Set the value
            current[keys[-1]] = value

        return result


class CitySelector(Container):
    """Widget for selecting and managing cities."""

    def __init__(self, cities: Optional[List[Dict[str, str]]] = None, **kwargs):
        """Initialize city selector."""
        super().__init__(**kwargs)
        self.cities = cities or []
        self.current_index = 0

    def compose(self) -> ComposeResult:
        """Compose the city selector."""
        with Vertical():
            yield Label("Selected Cities:", classes="label")
            yield DataTable(id="cities-table")
            with Horizontal(classes="button-row"):
                yield Button("← Previous", id="prev-city", variant="default")
                yield Button("Next →", id="next-city", variant="default")
                yield Button("Add", id="add-city-btn", variant="primary")
                yield Button("Remove", id="remove-city-btn", variant="warning")

    def on_mount(self) -> None:
        """Initialize the cities table."""
        self.update_cities_table()

    def update_cities_table(self) -> None:
        """Update the cities table display."""
        table = self.query_one("#cities-table", DataTable)
        table.clear(columns=True)

        table.add_column("City", key="city")
        table.add_column("State", key="state")
        table.add_column("Country", key="country")

        for i, city in enumerate(self.cities):
            style = "bold yellow" if i == self.current_index else None
            table.add_row(
                city.get("name", ""),
                city.get("state", ""),
                city.get("country", ""),
                key=str(i)
            )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "prev-city":
            if self.cities:
                self.current_index = (self.current_index - 1) % len(self.cities)
                self.update_cities_table()

        elif button_id == "next-city":
            if self.cities:
                self.current_index = (self.current_index + 1) % len(self.cities)
                self.update_cities_table()

    def get_current_city(self) -> Optional[Dict[str, str]]:
        """Get the currently selected city."""
        if 0 <= self.current_index < len(self.cities):
            return self.cities[self.current_index]
        return None

    def add_city(self, city_data: Dict[str, str]) -> None:
        """Add a new city."""
        self.cities.append(city_data)
        self.update_cities_table()

    def remove_current_city(self) -> None:
        """Remove the currently selected city."""
        if self.cities and 0 <= self.current_index < len(self.cities):
            del self.cities[self.current_index]
            if self.current_index >= len(self.cities) and self.cities:
                self.current_index = len(self.cities) - 1
            self.update_cities_table()


class CurrencySelector(Container):
    """Widget for selecting currencies."""

    POPULAR_CURRENCIES = [
        ("USD", "US Dollar"),
        ("EUR", "Euro"),
        ("GBP", "British Pound"),
        ("JPY", "Japanese Yen"),
        ("CHF", "Swiss Franc"),
        ("CAD", "Canadian Dollar"),
        ("AUD", "Australian Dollar"),
        ("CNY", "Chinese Yuan"),
        ("INR", "Indian Rupee"),
        ("BRL", "Brazilian Real"),
        ("MXN", "Mexican Peso"),
        ("KRW", "South Korean Won"),
        ("SGD", "Singapore Dollar"),
        ("HKD", "Hong Kong Dollar"),
        ("NOK", "Norwegian Krone"),
        ("SEK", "Swedish Krona"),
        ("DKK", "Danish Krone"),
        ("PLN", "Polish Złoty"),
        ("TRY", "Turkish Lira"),
        ("ZAR", "South African Rand")
    ]

    def __init__(self, selected_currencies: Optional[List[str]] = None, **kwargs):
        """Initialize currency selector."""
        super().__init__(**kwargs)
        self.selected_currencies = selected_currencies or ["USD", "EUR", "GBP"]

    def compose(self) -> ComposeResult:
        """Compose the currency selector."""
        with Vertical():
            yield Label("Base Currency:", classes="label")
            yield Select(
                options=[(c[0], f"{c[0]} - {c[1]}") for c in self.POPULAR_CURRENCIES],
                id="base-currency-select",
                value="USD"
            )

            yield Label("Target Currencies:", classes="label")
            yield Label("(Select one at a time - multiple selection not supported)", classes="warning-message")
            yield Select(
                options=[(c[0], f"{c[0]} - {c[1]}") for c in self.POPULAR_CURRENCIES],
                id="target-currencies-select",
                value=self.selected_currencies[0] if self.selected_currencies else "EUR"
            )

    def get_base_currency(self) -> str:
        """Get the selected base currency."""
        select = self.query_one("#base-currency-select", Select)
        return select.value or "USD"

    def get_target_currencies(self) -> List[str]:
        """Get the selected target currencies."""
        select = self.query_one("#target-currencies-select", Select)
        return select.value if isinstance(select.value, list) else [select.value] if select.value else []