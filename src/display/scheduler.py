"""Display scheduler for rotating content on e-ink display.

Inspired by InkyPi's playlist feature - allows scheduling different
plugins at designated times throughout the day.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, time, timedelta
from dataclasses import dataclass
from enum import Enum
from PIL import Image

from ..plugins import plugin_registry, PluginData
from .renderer import EInkRenderer


class DisplayMode(Enum):
    """Display modes for content rotation."""
    CYCLE = "cycle"          # Cycle through all plugins
    SCHEDULE = "schedule"     # Time-based schedule
    SINGLE = "single"        # Single plugin display
    COMPOSITE = "composite"  # Multiple plugins at once
    PRIORITY = "priority"    # Show based on priority


@dataclass
class ScheduleEntry:
    """Entry in the display schedule."""
    start_time: time
    end_time: time
    plugin_name: str
    display_mode: str = "single"
    config: Optional[Dict[str, Any]] = None


class DisplayScheduler:
    """Manages scheduled display rotation for e-ink."""

    def __init__(self, renderer: Optional[EInkRenderer] = None, cycle_interval: int = 30):
        """Initialize display scheduler."""
        self.logger = logging.getLogger("display_scheduler")
        self.renderer = renderer or EInkRenderer()

        # Schedule configuration
        self.mode = DisplayMode.CYCLE
        self.schedule: List[ScheduleEntry] = []
        self.current_plugin_index = 0

        # Timing configuration
        self.cycle_interval = cycle_interval  # seconds (configurable)
        self.last_update = None

        # Display state
        self.is_running = False
        self.current_task = None

        self.logger.info(f"Scheduler initialized with cycle_interval={cycle_interval}s")

    def set_mode(self, mode: DisplayMode):
        """Set the display mode."""
        self.mode = mode
        self.logger.info(f"Display mode set to: {mode.value}")

    def add_schedule_entry(self, entry: ScheduleEntry):
        """Add an entry to the schedule."""
        self.schedule.append(entry)
        # Sort by start time
        self.schedule.sort(key=lambda x: x.start_time)
        self.logger.info(f"Added schedule entry: {entry.plugin_name} at {entry.start_time}")

    def clear_schedule(self):
        """Clear all schedule entries."""
        self.schedule.clear()
        self.logger.info("Schedule cleared")

    def get_current_plugin(self) -> Optional[str]:
        """Get the plugin that should be displayed based on mode and schedule."""
        if self.mode == DisplayMode.SCHEDULE:
            return self._get_scheduled_plugin()
        elif self.mode == DisplayMode.CYCLE:
            return self._get_next_cycle_plugin()
        elif self.mode == DisplayMode.SINGLE:
            # Return first enabled plugin instance ID
            instance_ids = list(plugin_registry.plugins.keys())
            enabled_ids = [id for id in instance_ids if plugin_registry.plugins[id].config.enabled]
            return enabled_ids[0] if enabled_ids else None
        elif self.mode == DisplayMode.PRIORITY:
            return self._get_priority_plugin()
        else:
            return None

    def _get_scheduled_plugin(self) -> Optional[str]:
        """Get plugin based on schedule."""
        now = datetime.now().time()

        for entry in self.schedule:
            # Handle schedules that cross midnight
            if entry.start_time <= entry.end_time:
                if entry.start_time <= now <= entry.end_time:
                    return entry.plugin_name
            else:
                # Crosses midnight
                if now >= entry.start_time or now <= entry.end_time:
                    return entry.plugin_name

        # No scheduled entry - use default
        return self._get_next_cycle_plugin()

    def _get_next_cycle_plugin(self) -> Optional[str]:
        """Get next plugin in cycle - returns instance ID."""
        plugins = plugin_registry.get_enabled_plugins()
        if not plugins:
            return None

        # Get the instance ID from the registry
        instance_ids = list(plugin_registry.plugins.keys())
        enabled_ids = [id for id in instance_ids if plugin_registry.plugins[id].config.enabled]

        if not enabled_ids:
            return None

        instance_id = enabled_ids[self.current_plugin_index % len(enabled_ids)]
        return instance_id

    def _get_priority_plugin(self) -> Optional[str]:
        """Get highest priority plugin instance ID with fresh data."""
        instance_ids = list(plugin_registry.plugins.keys())
        enabled_plugins = [(id, plugin_registry.plugins[id]) for id in instance_ids
                          if plugin_registry.plugins[id].config.enabled]

        if not enabled_plugins:
            return None

        # Sort by priority
        sorted_plugins = sorted(enabled_plugins, key=lambda x: x[1].config.priority, reverse=True)
        return sorted_plugins[0][0] if sorted_plugins else None

    def advance_cycle(self):
        """Move to next plugin in cycle."""
        plugins = plugin_registry.get_enabled_plugins()
        if plugins:
            self.current_plugin_index = (self.current_plugin_index + 1) % len(plugins)
            self.logger.debug(f"Advanced to plugin index: {self.current_plugin_index}")

    async def render_current(self) -> Image.Image:
        """Render the current display content."""
        if self.mode == DisplayMode.COMPOSITE:
            return await self._render_composite()
        else:
            plugin_name = self.get_current_plugin()
            if plugin_name:
                return await self._render_single(plugin_name)
            else:
                return self.renderer.create_splash_screen("No Active Plugins")

    async def _render_single(self, plugin_name: str) -> Image.Image:
        """Render a single plugin."""
        plugin = plugin_registry.get_plugin(plugin_name)
        if not plugin:
            self.logger.error(f"Plugin instance '{plugin_name}' not found in registry")
            available = list(plugin_registry.plugins.keys())
            self.logger.error(f"Available instances: {available}")
            return self.renderer.create_splash_screen(f"Plugin {plugin_name} not found")

        try:
            # Get plugin data
            plugin_data = await plugin.update()

            # Render for e-ink
            return self.renderer.render_plugin(plugin_data)

        except Exception as e:
            self.logger.error(f"Failed to render {plugin_name}: {e}")
            return self.renderer.create_splash_screen(f"Error: {plugin_name}")

    async def _render_composite(self) -> Image.Image:
        """Render multiple plugins in composite layout."""
        plugins = plugin_registry.get_enabled_plugins()
        if not plugins:
            return self.renderer.create_splash_screen("No Active Plugins")

        # Collect plugin data
        plugins_data = []
        for plugin in plugins[:4]:  # Limit to 4 for display space
            try:
                data = await plugin.update()
                plugins_data.append(data)
            except Exception as e:
                self.logger.error(f"Failed to get data from {plugin.name}: {e}")

        if plugins_data:
            # Determine layout based on plugin count
            if len(plugins_data) <= 2:
                layout = "list"
            elif len(plugins_data) <= 4:
                layout = "grid"
            else:
                layout = "dashboard"

            return self.renderer.render_composite(plugins_data, layout)
        else:
            return self.renderer.create_splash_screen("No Plugin Data Available")

    async def run(self):
        """Main scheduler loop."""
        self.is_running = True
        self.logger.info(f"Display scheduler started in {self.mode.value} mode")

        try:
            while self.is_running:
                # Render current display
                image = await self.render_current()

                # Here you would send the image to the actual e-ink display
                # For now, we'll just log it
                self.logger.info(f"Display updated with mode: {self.mode.value}")
                self.last_update = datetime.now()

                # Advance cycle if in cycle mode
                if self.mode == DisplayMode.CYCLE:
                    self.advance_cycle()

                # Wait for next update
                await asyncio.sleep(self.cycle_interval)

        except asyncio.CancelledError:
            self.logger.info("Display scheduler cancelled")
        except Exception as e:
            self.logger.error(f"Display scheduler error: {e}")
        finally:
            self.is_running = False

    async def start(self):
        """Start the scheduler."""
        if not self.is_running:
            self.current_task = asyncio.create_task(self.run())
            return self.current_task

    async def stop(self):
        """Stop the scheduler."""
        self.is_running = False
        if self.current_task:
            self.current_task.cancel()
            try:
                await self.current_task
            except asyncio.CancelledError:
                pass

    def create_default_schedule(self):
        """Create a default daily schedule."""
        # Morning: Weather and news
        self.add_schedule_entry(ScheduleEntry(
            start_time=time(6, 0),
            end_time=time(9, 0),
            plugin_name="weather",
            display_mode="single"
        ))

        # Work hours: Currency and crypto
        self.add_schedule_entry(ScheduleEntry(
            start_time=time(9, 0),
            end_time=time(17, 0),
            plugin_name="currency",
            display_mode="composite"
        ))

        # Evening: Weather and clock
        self.add_schedule_entry(ScheduleEntry(
            start_time=time(17, 0),
            end_time=time(22, 0),
            plugin_name="clock",
            display_mode="single"
        ))

        # Night: Clock only (less frequent updates)
        self.add_schedule_entry(ScheduleEntry(
            start_time=time(22, 0),
            end_time=time(6, 0),
            plugin_name="clock",
            display_mode="single",
            config={"update_interval": 300}  # 5 minute updates at night
        ))

        self.logger.info("Default schedule created")

    def get_schedule_info(self) -> List[Dict[str, Any]]:
        """Get schedule information for display."""
        return [
            {
                "start": entry.start_time.strftime("%H:%M"),
                "end": entry.end_time.strftime("%H:%M"),
                "plugin": entry.plugin_name,
                "mode": entry.display_mode,
                "config": entry.config
            }
            for entry in self.schedule
        ]

    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        return {
            "running": self.is_running,
            "mode": self.mode.value,
            "current_plugin": self.get_current_plugin(),
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "cycle_interval": self.cycle_interval,
            "schedule_entries": len(self.schedule),
            "current_index": self.current_plugin_index
        }