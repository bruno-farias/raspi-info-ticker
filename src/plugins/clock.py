"""Clock plugin for the info ticker."""

from typing import Dict, Any, Optional
from datetime import datetime
import pytz
from zoneinfo import ZoneInfo
from pydantic import BaseModel, Field

from .base import BasePlugin, PluginConfig


class ClockPluginConfig(PluginConfig):
    """Configuration for clock plugin."""
    timezone: Optional[str] = Field(None, description="Timezone (e.g., 'UTC', 'US/Eastern')")
    format_24h: bool = Field(default=True, description="Use 24-hour format")
    show_date: bool = Field(default=True, description="Show date")
    show_seconds: bool = Field(default=True, description="Show seconds")
    date_format: str = Field(default="%Y-%m-%d", description="Date format string")
    show_day_name: bool = Field(default=True, description="Show day name")
    show_week_number: bool = Field(default=False, description="Show week number")


class ClockPlugin(BasePlugin):
    """Plugin for displaying clock and date information."""

    name = "clock"
    version = "1.0.0"
    description = "Clock & Date"
    author = "System"

    def __init__(self, config: Optional[ClockPluginConfig] = None):
        """Initialize clock plugin."""
        super().__init__(config or ClockPluginConfig())
        # Disable caching for clock
        self.config.cache_ttl = 0

    def get_config_schema(self) -> type[BaseModel]:
        """Get configuration schema."""
        return ClockPluginConfig

    async def fetch_data(self) -> Dict[str, Any]:
        """Get current time and date."""
        # Get current time in specified timezone
        if self.config.timezone:
            try:
                tz = ZoneInfo(self.config.timezone)
                now = datetime.now(tz)
            except Exception:
                # Fallback to pytz if zoneinfo fails
                try:
                    tz = pytz.timezone(self.config.timezone)
                    now = datetime.now(tz)
                except Exception as e:
                    self.logger.warning(f"Invalid timezone {self.config.timezone}: {e}")
                    now = datetime.now()
        else:
            now = datetime.now()

        return {
            "datetime": now,
            "timestamp": now.timestamp(),
            "iso": now.isoformat(),
            "timezone": self.config.timezone or "Local"
        }

    def get_display_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format clock data for display."""
        dt = data.get("datetime")
        if not dt:
            dt = datetime.now()

        # Format time
        if self.config.format_24h:
            time_format = "%H:%M:%S" if self.config.show_seconds else "%H:%M"
        else:
            time_format = "%I:%M:%S %p" if self.config.show_seconds else "%I:%M %p"

        display = {
            "time": dt.strftime(time_format),
            "timezone": data.get("timezone", "Local")
        }

        # Add date if enabled
        if self.config.show_date:
            display["date"] = dt.strftime(self.config.date_format)

        # Add day name if enabled
        if self.config.show_day_name:
            display["day_name"] = dt.strftime("%A")

        # Add week number if enabled
        if self.config.show_week_number:
            display["week_number"] = dt.strftime("Week %W")

        # Add additional time components
        display.update({
            "hour": dt.hour,
            "minute": dt.minute,
            "second": dt.second,
            "year": dt.year,
            "month": dt.month,
            "day": dt.day,
            "month_name": dt.strftime("%B"),
            "short_month": dt.strftime("%b"),
            "short_day": dt.strftime("%a")
        })

        # Create formatted display lines
        lines = [display["time"]]
        if self.config.show_date:
            date_line = display["date"]
            if self.config.show_day_name:
                date_line = f"{display['day_name']}, {date_line}"
            lines.append(date_line)
        if self.config.show_week_number:
            lines.append(display["week_number"])
        if self.config.timezone:
            lines.append(f"TZ: {display['timezone']}")

        display["formatted_lines"] = lines

        return display

    def get_widget_layout(self) -> Dict[str, Any]:
        """Get widget layout preferences."""
        height = 3
        if self.config.show_date:
            height += 1
        if self.config.show_week_number:
            height += 1
        if self.config.timezone:
            height += 1

        return {
            "type": "clock",
            "min_width": 20,
            "min_height": height,
            "expandable": False,
            "resizable": True
        }

    def supports_interaction(self) -> bool:
        """Clock plugin supports timezone changes."""
        return True

    async def handle_interaction(self, action: str, params: Dict[str, Any]) -> Any:
        """Handle user interactions."""
        if action == "change_timezone":
            tz = params.get("timezone")
            if tz:
                # Validate timezone
                try:
                    if tz == "Local":
                        self.config.timezone = None
                    else:
                        # Test if timezone is valid
                        test_tz = ZoneInfo(tz)
                        self.config.timezone = tz
                    return {"success": True, "timezone": self.config.timezone or "Local"}
                except Exception:
                    try:
                        # Try pytz as fallback
                        test_tz = pytz.timezone(tz)
                        self.config.timezone = tz
                        return {"success": True, "timezone": self.config.timezone}
                    except Exception:
                        return {"success": False, "error": "Invalid timezone"}
            return {"success": False, "error": "No timezone provided"}

        elif action == "toggle_24h":
            self.config.format_24h = not self.config.format_24h
            return {"success": True, "format_24h": self.config.format_24h}

        elif action == "toggle_date":
            self.config.show_date = not self.config.show_date
            return {"success": True, "show_date": self.config.show_date}

        elif action == "toggle_seconds":
            self.config.show_seconds = not self.config.show_seconds
            return {"success": True, "show_seconds": self.config.show_seconds}

        elif action == "set_date_format":
            fmt = params.get("format")
            if fmt:
                try:
                    # Test format
                    datetime.now().strftime(fmt)
                    self.config.date_format = fmt
                    return {"success": True, "date_format": self.config.date_format}
                except Exception:
                    return {"success": False, "error": "Invalid date format"}
            return {"success": False, "error": "No format provided"}

        elif action == "get_timezones":
            # Return common timezones
            common_tzs = [
                "Local",
                "UTC",
                "US/Eastern",
                "US/Central",
                "US/Mountain",
                "US/Pacific",
                "Europe/London",
                "Europe/Paris",
                "Europe/Berlin",
                "Asia/Tokyo",
                "Asia/Shanghai",
                "Asia/Singapore",
                "Australia/Sydney",
                "America/New_York",
                "America/Chicago",
                "America/Denver",
                "America/Los_Angeles",
                "America/Sao_Paulo",
                "Africa/Cairo",
                "Asia/Dubai"
            ]
            return {"success": True, "timezones": common_tzs}

        return {"success": False, "error": f"Unknown action: {action}"}