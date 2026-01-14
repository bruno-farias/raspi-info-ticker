"""Enhanced display runner for e-ink focused operation.

This runner prioritizes e-ink display as the primary output with:
- Optimized rendering for e-paper
- Scheduled content rotation
- Minimal resource usage
- Web interface for management only
"""

import asyncio
import logging
import signal
from typing import Optional
from datetime import datetime
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.config import config_manager
from src.plugins import plugin_registry
from src.display.renderer import EInkRenderer
from src.display.scheduler import DisplayScheduler, DisplayMode

# Make management interface optional
try:
    from src.web.management import ManagementInterface
    MANAGEMENT_AVAILABLE = True
except ImportError:
    MANAGEMENT_AVAILABLE = False
    ManagementInterface = None


class EnhancedDisplayRunner:
    """Enhanced runner focused on e-ink display with management interface."""

    def __init__(self):
        """Initialize enhanced display runner."""
        self.logger = logging.getLogger("enhanced_runner")
        self.config = None
        self.epd = None  # E-paper display instance
        self.renderer = None
        self.scheduler = None
        self.management = None
        self.running = False

        # Display state
        self.partial_refresh_count = 0
        self.full_refresh_interval = 20

    async def initialize(self):
        """Initialize all components."""
        self.logger.info("Initializing Enhanced Display Runner...")

        # Load configuration
        self.config = config_manager.load(create_if_missing=True)
        self.logger.info("Configuration loaded")

        # Initialize renderer first (needed for splash screen)
        self.renderer = EInkRenderer(width=250, height=122)

        # Initialize e-paper display
        self._init_epaper()

        # Update renderer dimensions if e-paper is available
        if self.epd:
            self.renderer = EInkRenderer(
                width=self.epd.height,  # Note: rotated for landscape
                height=self.epd.width
            )

        # Initialize scheduler with config cycle interval
        cycle_interval = self.config.display.cycle_interval if self.config and self.config.display else 30
        self.logger.info(f"Using cycle interval: {cycle_interval} seconds")
        self.scheduler = DisplayScheduler(self.renderer, cycle_interval=cycle_interval)
        self._configure_scheduler()

        # Initialize plugins
        await self._init_plugins()

        # Start management interface if enabled
        if self.config.web_server.enabled:
            await self._start_management_interface()

        self.logger.info("Enhanced Display Runner initialized successfully")

    def _init_epaper(self):
        """Initialize e-paper display hardware."""
        try:
            # Import display library
            libdir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'waveshare_epd'
            )
            if os.path.exists(libdir):
                sys.path.append(os.path.dirname(libdir))

            from waveshare_epd import epd2in13_V4
            self.epd = epd2in13_V4.EPD()
            self.epd.init()
            self.epd.Clear(0xFF)

            self.logger.info("E-paper display initialized")

            # Show splash screen
            splash = self.renderer.create_splash_screen("Starting...")
            self._display_image(splash)

        except Exception as e:
            self.logger.warning(f"E-paper initialization failed: {e}")
            self.logger.info("Running in simulation mode")
            self.epd = None

    def _configure_scheduler(self):
        """Configure the display scheduler based on settings."""
        # Set display mode
        mode_map = {
            "cycle": DisplayMode.CYCLE,
            "schedule": DisplayMode.SCHEDULE,
            "single": DisplayMode.SINGLE,
            "composite": DisplayMode.COMPOSITE,
            "priority": DisplayMode.PRIORITY
        }

        display_mode = self.config.display.mode if self.config else "cycle"
        if display_mode in mode_map:
            self.scheduler.set_mode(mode_map[display_mode])
        else:
            self.scheduler.set_mode(DisplayMode.CYCLE)

        # Set cycle interval
        self.scheduler.cycle_interval = self.config.display.refresh_interval

        # Load schedule if available
        # TODO: Load from config or file
        if self.scheduler.mode == DisplayMode.SCHEDULE:
            self.scheduler.create_default_schedule()

    async def _init_plugins(self):
        """Initialize plugins based on configuration."""
        # Discover built-in plugins
        plugin_registry.discover_plugins()

        # Create enabled plugins
        if self.config:
            plugins_config = self.config.plugins

            # Weather - create one instance per city
            if plugins_config.weather.enabled and plugins_config.weather.cities:
                for idx, city in enumerate(plugins_config.weather.cities):
                    # Create a copy of weather config for this specific city
                    from copy import deepcopy
                    city_config = deepcopy(plugins_config.weather)
                    city_config.cities = [city]  # Only this city
                    city_config.current_city_index = 0

                    # Create instance with unique ID
                    city_name = city.get("name", f"city_{idx}")
                    instance_id = f"weather_{city_name.lower().replace(' ', '_')}"
                    plugin_registry.create_plugin("weather", city_config, instance_id=instance_id)

            # Currency - create one instance per base currency if multiple configs specified
            if plugins_config.currency.enabled:
                if plugins_config.currency.currencies:
                    # Multiple currency configurations
                    for idx, curr_config in enumerate(plugins_config.currency.currencies):
                        # Create a copy of currency config for this specific base
                        from copy import deepcopy
                        base_config = deepcopy(plugins_config.currency)
                        base_config.base_currency = curr_config.get("base_currency", "USD")
                        base_config.target_currencies = curr_config.get("target_currencies", ["EUR"])
                        base_config.currencies = None  # Clear to avoid recursion

                        # Create instance with unique ID
                        base_name = base_config.base_currency.lower()
                        instance_id = f"currency_{base_name}"
                        plugin_registry.create_plugin("currency", base_config, instance_id=instance_id)
                        self.logger.info(f"Created currency instance: {instance_id} -> {base_config.target_currencies}")
                else:
                    # Single currency configuration
                    plugin_registry.create_plugin("currency", plugins_config.currency)

            # Crypto
            if plugins_config.crypto.enabled:
                plugin_registry.create_plugin("crypto", plugins_config.crypto)

            # Clock (moved to end of cycle)
            if plugins_config.clock.enabled:
                plugin_registry.create_plugin("clock", plugins_config.clock)

        # Initialize all plugins
        await plugin_registry.initialize_all()
        self.logger.info(f"Initialized {len(plugin_registry.get_enabled_plugins())} plugins")

    async def _start_management_interface(self):
        """Start the web management interface."""
        if not MANAGEMENT_AVAILABLE:
            self.logger.warning("Management interface not available (missing dependencies)")
            return

        try:
            self.management = ManagementInterface(
                host=self.config.web_server.host,
                port=self.config.web_server.port
            )

            # Start in background
            asyncio.create_task(self.management.run())
            self.logger.info(
                f"Management interface started at "
                f"http://{self.config.web_server.host}:{self.config.web_server.port}"
            )

        except Exception as e:
            self.logger.error(f"Failed to start management interface: {e}")

    async def run(self):
        """Main display loop."""
        self.running = True
        self.logger.info("Display loop started")

        try:
            cycle_start_time = asyncio.get_event_loop().time()
            current_displayed_plugin = None

            while self.running:
                # Get current plugin instance ID
                current_plugin_name = self.scheduler.get_current_plugin()
                is_clock = current_plugin_name and current_plugin_name.startswith("clock")

                # Check if we switched to a new plugin
                if current_plugin_name != current_displayed_plugin:
                    cycle_start_time = asyncio.get_event_loop().time()
                    current_displayed_plugin = current_plugin_name
                    self.logger.info(f"Displaying plugin: {current_plugin_name}")

                # Get and render current display content
                image = await self.scheduler.render_current()

                # Display on e-paper
                self._display_image(image)

                # Calculate time showing current plugin
                current_time = asyncio.get_event_loop().time()
                time_on_current = current_time - cycle_start_time

                # Check if it's time to advance to next plugin
                if self.scheduler.mode == DisplayMode.CYCLE:
                    if time_on_current >= self.scheduler.cycle_interval:
                        self.scheduler.advance_cycle()
                        # Don't reset timer here - it will reset on next iteration when plugin changes

                # Update interval: 1 second for clock (live updates), cycle_interval for others
                if is_clock:
                    await asyncio.sleep(1)  # Live clock updates every second
                else:
                    # Sleep for remaining time until cycle completes
                    remaining_time = self.scheduler.cycle_interval - time_on_current
                    if remaining_time > 0:
                        await asyncio.sleep(remaining_time)
                    else:
                        await asyncio.sleep(0.1)  # Small sleep to avoid busy loop

        except asyncio.CancelledError:
            self.logger.info("Display loop cancelled")
        except Exception as e:
            self.logger.error(f"Display loop error: {e}")
            # Show error on display
            error_image = self.renderer.create_splash_screen(f"Error: {str(e)[:20]}")
            self._display_image(error_image)
        finally:
            self.running = False

    def _display_image(self, image):
        """Display image on e-paper with smart refresh."""
        if self.epd:
            try:
                self.partial_refresh_count += 1

                # Determine refresh type
                if self.partial_refresh_count >= self.full_refresh_interval:
                    # Full refresh to prevent ghosting
                    self.logger.debug("Performing full refresh")
                    self.epd.init()
                    self.epd.display(self.epd.getbuffer(image))
                    self.partial_refresh_count = 0
                else:
                    # Partial refresh for smooth updates
                    self.logger.debug("Performing partial refresh")
                    if self.partial_refresh_count == 1:
                        # First partial needs base image
                        self.epd.displayPartBaseImage(self.epd.getbuffer(image))
                    else:
                        self.epd.displayPartial(self.epd.getbuffer(image))

            except Exception as e:
                self.logger.error(f"Display update failed: {e}")
        else:
            # Simulation mode - save to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"display_sim_{timestamp}.png"
            image.save(filename)
            self.logger.debug(f"Simulation: saved {filename}")

    async def cleanup(self):
        """Cleanup resources."""
        self.logger.info("Cleaning up...")
        self.running = False

        # Stop scheduler
        if self.scheduler:
            await self.scheduler.stop()

        # Cleanup plugins
        await plugin_registry.cleanup_all()

        # Clear and sleep display
        if self.epd:
            try:
                self.epd.Clear(0xFF)
                self.epd.sleep()
                self.logger.info("E-paper display cleared and sleeping")
            except Exception as e:
                self.logger.error(f"Display cleanup failed: {e}")

        self.logger.info("Cleanup complete")

    def handle_shutdown(self, signum, frame):
        """Handle shutdown signal."""
        self.logger.info(f"Shutdown signal received: {signum}")
        self.running = False


async def main():
    """Main entry point for enhanced display runner."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create and initialize runner
    runner = EnhancedDisplayRunner()

    # Setup signal handlers
    signal.signal(signal.SIGINT, runner.handle_shutdown)
    signal.signal(signal.SIGTERM, runner.handle_shutdown)

    try:
        # Initialize
        await runner.initialize()

        # Run display loop
        await runner.run()

    except Exception as e:
        logging.error(f"Fatal error: {e}")
    finally:
        # Cleanup
        await runner.cleanup()


if __name__ == "__main__":
    # Run the enhanced display runner
    asyncio.run(main())