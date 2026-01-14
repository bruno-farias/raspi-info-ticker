"""Weather plugin for the info ticker."""

import aiohttp
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from .base import BasePlugin, PluginConfig


class WeatherPluginConfig(PluginConfig):
    """Configuration for weather plugin."""
    api_key: str = Field(..., description="OpenWeatherMap API key")
    cities: List[Dict[str, str]] = Field(
        default=[{"name": "London", "country": "UK"}],
        description="List of cities to monitor"
    )
    units: str = Field(default="metric", description="Units: metric, imperial, kelvin")
    language: str = Field(default="en", description="Language code")
    show_forecast: bool = Field(default=False, description="Show weather forecast")
    current_city_index: int = Field(default=0, description="Currently selected city index")


class WeatherPlugin(BasePlugin):
    """Plugin for fetching and displaying weather data."""

    name = "weather"
    version = "1.0.0"
    description = "Weather Information"
    author = "System"

    def __init__(self, config: Optional[WeatherPluginConfig] = None):
        """Initialize weather plugin."""
        super().__init__(config or WeatherPluginConfig())
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.current_city_index = config.current_city_index if config else 0

    def get_config_schema(self) -> type[BaseModel]:
        """Get configuration schema."""
        return WeatherPluginConfig

    async def fetch_data(self) -> Dict[str, Any]:
        """Fetch weather data from OpenWeatherMap API."""
        if not self.config.api_key:
            raise ValueError("Weather API key not configured")

        if not self.config.cities:
            raise ValueError("No cities configured")

        # Get first (and only) city for this instance
        city = self.config.cities[0]

        # Build location string
        location_parts = [city.get("name", "")]
        if "state" in city:
            location_parts.append(city["state"])
        if "country" in city:
            location_parts.append(city["country"])
        location = ",".join(location_parts)

        # Fetch current weather
        async with aiohttp.ClientSession() as session:
            params = {
                "q": location,
                "appid": self.config.api_key,
                "units": self.config.units,
                "lang": self.config.language
            }

            async with session.get(f"{self.base_url}/weather", params=params) as response:
                response.raise_for_status()
                weather_data = await response.json()

            # Optionally fetch forecast
            forecast_data = None
            if self.config.show_forecast:
                async with session.get(f"{self.base_url}/forecast", params=params) as response:
                    response.raise_for_status()
                    forecast_data = await response.json()

        return {
            "current": weather_data,
            "forecast": forecast_data,
            "city_info": city
        }

    def get_display_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format weather data for display."""
        current = data.get("current", {})
        city_info = data.get("city_info", {})

        if not current:
            return {"error": "No weather data available"}

        # Extract main weather info
        main = current.get("main", {})
        weather = current.get("weather", [{}])[0]
        wind = current.get("wind", {})
        clouds = current.get("clouds", {})
        sys_info = current.get("sys", {})

        display = {
            "city": current.get("name", city_info.get("name", "Unknown")),
            "country": sys_info.get("country", city_info.get("country", "")),
            "temperature": round(main.get("temp", 0), 1),
            "feels_like": round(main.get("feels_like", 0), 1),
            "temp_min": round(main.get("temp_min", 0), 1),
            "temp_max": round(main.get("temp_max", 0), 1),
            "pressure": main.get("pressure", 0),
            "humidity": main.get("humidity", 0),
            "visibility": current.get("visibility", 0),
            "description": weather.get("description", "").title(),
            "icon": weather.get("icon", "01d"),
            "wind_speed": wind.get("speed", 0),
            "wind_direction": wind.get("deg", 0),
            "clouds": clouds.get("all", 0),
            "sunrise": datetime.fromtimestamp(sys_info.get("sunrise", 0)).strftime("%H:%M") if sys_info.get("sunrise") else "N/A",
            "sunset": datetime.fromtimestamp(sys_info.get("sunset", 0)).strftime("%H:%M") if sys_info.get("sunset") else "N/A",
            "units": self.config.units,
            "all_cities": data.get("all_cities", []),
            "current_city_index": self.current_city_index
        }

        # Add forecast if available
        if data.get("forecast"):
            forecast_list = data["forecast"].get("list", [])[:5]  # Next 5 forecasts (15 hours)
            display["forecast"] = [
                {
                    "time": datetime.fromtimestamp(f.get("dt", 0)).strftime("%H:%M"),
                    "temp": round(f["main"]["temp"], 1),
                    "description": f["weather"][0]["description"].title(),
                    "icon": f["weather"][0]["icon"]
                }
                for f in forecast_list
            ]

        return display

    def get_widget_layout(self) -> Dict[str, Any]:
        """Get widget layout preferences."""
        return {
            "type": "weather",
            "min_width": 30,
            "min_height": 8,
            "expandable": True,
            "resizable": True
        }

    def supports_interaction(self) -> bool:
        """Weather plugin supports city selection."""
        return True

    async def handle_interaction(self, action: str, params: Dict[str, Any]) -> Any:
        """
        Handle user interactions.

        Supported actions:
        - next_city: Switch to next city
        - prev_city: Switch to previous city
        - select_city: Select specific city by index
        """
        if action == "next_city":
            self.current_city_index = (self.current_city_index + 1) % len(self.config.cities)
            self.config.current_city_index = self.current_city_index
            # Clear cache to force refresh
            self._last_data = None
            self._last_update = None
            return {"success": True, "current_city_index": self.current_city_index}

        elif action == "prev_city":
            self.current_city_index = (self.current_city_index - 1) % len(self.config.cities)
            self.config.current_city_index = self.current_city_index
            # Clear cache to force refresh
            self._last_data = None
            self._last_update = None
            return {"success": True, "current_city_index": self.current_city_index}

        elif action == "select_city":
            index = params.get("index", 0)
            if 0 <= index < len(self.config.cities):
                self.current_city_index = index
                self.config.current_city_index = self.current_city_index
                # Clear cache to force refresh
                self._last_data = None
                self._last_update = None
                return {"success": True, "current_city_index": self.current_city_index}
            else:
                return {"success": False, "error": "Invalid city index"}

        elif action == "add_city":
            city_data = params.get("city", {})
            if city_data and "name" in city_data:
                self.config.cities.append(city_data)
                return {"success": True, "cities": self.config.cities}
            else:
                return {"success": False, "error": "Invalid city data"}

        elif action == "remove_city":
            index = params.get("index", -1)
            if 0 <= index < len(self.config.cities):
                if len(self.config.cities) > 1:  # Keep at least one city
                    del self.config.cities[index]
                    # Adjust current index if necessary
                    if self.current_city_index >= len(self.config.cities):
                        self.current_city_index = len(self.config.cities) - 1
                        self.config.current_city_index = self.current_city_index
                    return {"success": True, "cities": self.config.cities}
                else:
                    return {"success": False, "error": "Cannot remove last city"}
            else:
                return {"success": False, "error": "Invalid city index"}

        else:
            return {"success": False, "error": f"Unknown action: {action}"}

    def get_weather_icon_url(self, icon_code: str) -> str:
        """Get URL for weather icon."""
        return f"https://openweathermap.org/img/wn/{icon_code}@2x.png"

    def get_unit_symbol(self) -> str:
        """Get temperature unit symbol."""
        units_map = {
            "metric": "°C",
            "imperial": "°F",
            "kelvin": "K"
        }
        return units_map.get(self.config.units, "°C")