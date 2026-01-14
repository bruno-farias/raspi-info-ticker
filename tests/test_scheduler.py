"""Tests for display scheduler."""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from PIL import Image

from src.display.scheduler import DisplayScheduler, DisplayMode, ScheduleEntry
from src.display.renderer import EInkRenderer
from src.plugins import plugin_registry, PluginConfig, PluginData


class MockPluginConfig(PluginConfig):
    """Mock plugin configuration for testing."""
    pass


class TestDisplayScheduler:
    """Test DisplayScheduler."""

    def test_init_default(self):
        """Test scheduler initialization with defaults."""
        scheduler = DisplayScheduler()

        assert scheduler.mode == DisplayMode.CYCLE
        assert scheduler.cycle_interval == 30
        assert scheduler.current_plugin_index == 0
        assert scheduler.is_running is False

    def test_init_with_renderer(self):
        """Test scheduler initialization with renderer."""
        renderer = EInkRenderer(width=250, height=122)
        scheduler = DisplayScheduler(renderer=renderer)

        assert scheduler.renderer is renderer

    def test_init_with_cycle_interval(self):
        """Test scheduler initialization with custom cycle interval."""
        scheduler = DisplayScheduler(cycle_interval=60)

        assert scheduler.cycle_interval == 60

    def test_set_mode(self):
        """Test setting display mode."""
        scheduler = DisplayScheduler()

        scheduler.set_mode(DisplayMode.SINGLE)
        assert scheduler.mode == DisplayMode.SINGLE

        scheduler.set_mode(DisplayMode.ALL)
        assert scheduler.mode == DisplayMode.ALL

    def test_add_schedule_entry(self):
        """Test adding schedule entry."""
        scheduler = DisplayScheduler()

        entry = ScheduleEntry(
            plugin_name="test",
            start_time="09:00",
            end_time="17:00",
            days_of_week=[0, 1, 2, 3, 4]  # Monday to Friday
        )

        scheduler.add_schedule(entry)

        assert len(scheduler.schedule) == 1
        assert scheduler.schedule[0].plugin_name == "test"

    def test_clear_schedule(self):
        """Test clearing schedule."""
        scheduler = DisplayScheduler()

        # Add some entries
        entry1 = ScheduleEntry(plugin_name="test1", start_time="09:00", end_time="17:00")
        entry2 = ScheduleEntry(plugin_name="test2", start_time="18:00", end_time="23:00")

        scheduler.add_schedule(entry1)
        scheduler.add_schedule(entry2)

        assert len(scheduler.schedule) == 2

        # Clear
        scheduler.clear_schedule()

        assert len(scheduler.schedule) == 0

    @pytest.mark.asyncio
    async def test_get_current_plugin_cycle_mode(self, fresh_plugin_registry):
        """Test getting current plugin in cycle mode."""
        from tests.test_plugins import MockPlugin, MockPluginConfig

        # Register and create test plugin
        fresh_plugin_registry.register_plugin_class(MockPlugin)
        fresh_plugin_registry.create_plugin("test", MockPluginConfig(enabled=True))

        scheduler = DisplayScheduler(cycle_interval=10)
        scheduler.set_mode(DisplayMode.CYCLE)

        # Get current plugin
        plugin_id = scheduler.get_current_plugin()

        # Should return an instance ID
        assert plugin_id is not None
        assert isinstance(plugin_id, str)

    def test_advance_cycle(self, fresh_plugin_registry):
        """Test advancing to next plugin in cycle."""
        from tests.test_plugins import MockPlugin, MockPluginConfig

        # Register and create multiple test plugins
        fresh_plugin_registry.register_plugin_class(MockPlugin)
        fresh_plugin_registry.create_plugin("test", MockPluginConfig(enabled=True), instance_id="test_1")
        fresh_plugin_registry.create_plugin("test", MockPluginConfig(enabled=True), instance_id="test_2")

        scheduler = DisplayScheduler()
        scheduler.set_mode(DisplayMode.CYCLE)

        initial_index = scheduler.current_plugin_index

        # Advance cycle
        scheduler.advance_cycle()

        # Index should increment
        assert scheduler.current_plugin_index == initial_index + 1

    @pytest.mark.asyncio
    async def test_render_current_plugin(self, fresh_plugin_registry):
        """Test rendering current plugin."""
        from tests.test_plugins import MockPlugin, MockPluginConfig

        # Register and create test plugin
        fresh_plugin_registry.register_plugin_class(MockPlugin)
        fresh_plugin_registry.create_plugin("test", MockPluginConfig(enabled=True))

        renderer = EInkRenderer(width=250, height=122)
        scheduler = DisplayScheduler(renderer=renderer)
        scheduler.set_mode(DisplayMode.CYCLE)

        # Render current
        image = await scheduler.render_current()

        assert image is not None
        assert isinstance(image, Image.Image)

    @pytest.mark.asyncio
    async def test_render_specific_plugin(self, fresh_plugin_registry):
        """Test rendering specific plugin by ID."""
        from tests.test_plugins import MockPlugin, MockPluginConfig

        # Register and create test plugin
        fresh_plugin_registry.register_plugin_class(MockPlugin)
        plugin = fresh_plugin_registry.create_plugin("test", MockPluginConfig(enabled=True), instance_id="test_specific")

        renderer = EInkRenderer(width=250, height=122)
        scheduler = DisplayScheduler(renderer=renderer)

        # Render specific plugin
        image = await scheduler.render_plugin("test_specific")

        assert image is not None
        assert isinstance(image, Image.Image)

    @pytest.mark.asyncio
    async def test_render_all_plugins(self, fresh_plugin_registry):
        """Test rendering all plugins."""
        from tests.test_plugins import MockPlugin, MockPluginConfig

        # Register and create multiple test plugins
        fresh_plugin_registry.register_plugin_class(MockPlugin)
        fresh_plugin_registry.create_plugin("test", MockPluginConfig(enabled=True), instance_id="test_1")
        fresh_plugin_registry.create_plugin("test", MockPluginConfig(enabled=True), instance_id="test_2")

        renderer = EInkRenderer(width=250, height=122)
        scheduler = DisplayScheduler(renderer=renderer)
        scheduler.set_mode(DisplayMode.ALL)

        # Render all
        image = await scheduler.render_all()

        assert image is not None
        assert isinstance(image, Image.Image)

    def test_get_enabled_plugin_count(self, fresh_plugin_registry):
        """Test getting count of enabled plugins."""
        from tests.test_plugins import MockPlugin, MockPluginConfig

        # Register and create plugins
        fresh_plugin_registry.register_plugin_class(MockPlugin)
        fresh_plugin_registry.create_plugin("test", MockPluginConfig(enabled=True), instance_id="test_enabled")
        fresh_plugin_registry.create_plugin("test", MockPluginConfig(enabled=False), instance_id="test_disabled")

        scheduler = DisplayScheduler()

        enabled_plugins = plugin_registry.get_enabled_plugins()
        assert len(enabled_plugins) >= 1  # At least the enabled one


class TestDisplayMode:
    """Test DisplayMode enum."""

    def test_display_modes(self):
        """Test display mode values."""
        assert DisplayMode.SINGLE.value == "single"
        assert DisplayMode.CYCLE.value == "cycle"
        assert DisplayMode.ALL.value == "all"
        assert DisplayMode.SCHEDULE.value == "schedule"

    def test_display_mode_comparison(self):
        """Test display mode comparison."""
        assert DisplayMode.SINGLE == DisplayMode.SINGLE
        assert DisplayMode.CYCLE != DisplayMode.SINGLE


class TestScheduleEntry:
    """Test ScheduleEntry."""

    def test_schedule_entry_creation(self):
        """Test creating schedule entry."""
        entry = ScheduleEntry(
            plugin_name="weather",
            start_time="09:00",
            end_time="17:00",
            days_of_week=[0, 1, 2, 3, 4]
        )

        assert entry.plugin_name == "weather"
        assert entry.start_time == "09:00"
        assert entry.end_time == "17:00"
        assert entry.days_of_week == [0, 1, 2, 3, 4]

    def test_schedule_entry_defaults(self):
        """Test schedule entry with defaults."""
        entry = ScheduleEntry(
            plugin_name="clock",
            start_time="00:00",
            end_time="23:59"
        )

        assert entry.plugin_name == "clock"
        # Should have default days_of_week (all days)
        assert entry.days_of_week == list(range(7))

    def test_schedule_entry_validation(self):
        """Test schedule entry time validation."""
        # Valid entry
        entry = ScheduleEntry(
            plugin_name="test",
            start_time="08:00",
            end_time="20:00"
        )

        assert entry.start_time == "08:00"
        assert entry.end_time == "20:00"
