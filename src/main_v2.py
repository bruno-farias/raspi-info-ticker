#!/usr/bin/env python3
"""Main entry point for Raspi Info Ticker v2.0 - E-ink focused architecture.

Key changes:
- E-ink display is the primary output
- TUI removed (not suitable for Pi Zero W)
- Web interface is for management only
- Optimized for minimal resource usage
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import config_manager
from src.plugins import plugin_registry


def run_display(args):
    """Run in e-ink display mode (primary operation)."""
    setup_logging(args.log_level)
    logging.info("Starting Raspi Info Ticker - E-ink Display Mode")

    from src.display.runner_v2 import main as display_main
    asyncio.run(display_main())


def run_management(args):
    """Run management web interface only."""
    setup_logging(args.log_level)
    logging.info("Starting Management Interface")

    from src.web.management import run_management_server
    run_management_server(host=args.host, port=args.port)


def run_preview(args):
    """Generate a preview of what would be displayed."""
    setup_logging(args.log_level)
    logging.info("Generating display preview...")

    async def generate_preview():
        # Initialize plugins
        config = config_manager.load()
        plugin_registry.discover_plugins()

        # Create a plugin instance
        if args.plugin:
            plugin = plugin_registry.create_plugin(args.plugin)
            if plugin:
                data = await plugin.update()

                from src.display.renderer import EInkRenderer
                renderer = EInkRenderer()
                image = renderer.render_plugin(data)

                # Save preview
                output = args.output or f"preview_{args.plugin}.png"
                image.save(output)
                print(f"Preview saved to {output}")
            else:
                print(f"Plugin {args.plugin} not found")
        else:
            print("Please specify a plugin with --plugin")

    asyncio.run(generate_preview())


def test_display(args):
    """Test e-paper display connection."""
    setup_logging(args.log_level)
    logging.info("Testing e-paper display...")

    try:
        # Import display library
        from waveshare_epd import epd2in13_V4

        # Initialize display
        epd = epd2in13_V4.EPD()
        epd.init()

        print("✓ Display connected successfully")
        print(f"  Width: {epd.height}px")
        print(f"  Height: {epd.width}px")

        if args.pattern:
            print("Displaying test pattern...")

            from PIL import Image, ImageDraw
            from src.display.renderer import EInkRenderer

            # Create test pattern
            renderer = EInkRenderer(epd.height, epd.width)
            image = renderer.create_splash_screen("Display Test OK")

            # Display it
            epd.display(epd.getbuffer(image))
            print("✓ Test pattern displayed")

        # Clean up
        epd.sleep()
        print("✓ Display test complete")

    except Exception as e:
        print(f"✗ Display test failed: {e}")
        sys.exit(1)


def list_plugins(args):
    """List available plugins."""
    setup_logging(args.log_level)

    # Discover plugins
    plugin_registry.discover_plugins()

    print("\nAvailable Plugins:")
    print("-" * 60)

    for info in plugin_registry.get_plugin_info():
        status = "✓" if info.get("active") else " "
        enabled = "ENABLED" if info.get("enabled") else "disabled"

        print(f"[{status}] {info['name']:15} v{info['version']:8} [{enabled:8}]")
        print(f"    {info['description']}")
        print(f"    Author: {info['author']}")
        print()


def create_config(args):
    """Create or validate configuration."""
    setup_logging(args.log_level)

    if args.validate:
        # Validate existing config
        try:
            config = config_manager.load(create_if_missing=False)
            print("✓ Configuration is valid")
            print(f"  Loaded from: {config_manager.config_path}")
        except Exception as e:
            print(f"✗ Configuration validation failed: {e}")
            sys.exit(1)
    else:
        # Create config
        config = config_manager.load(create_if_missing=True)

        if args.output:
            config_manager.save(Path(args.output))
            print(f"Configuration saved to {args.output}")
        else:
            config_manager.save()
            print(f"Configuration saved to {config_manager.config_path}")

        print("\nNext steps:")
        print("1. Edit the configuration file and add your API keys")
        print("2. Run: python src/main_v2.py display")


def setup_logging(level: str = "INFO"):
    """Setup logging configuration."""
    # Configure based on environment (Pi Zero W needs minimal logging)
    if os.getenv("PI_ZERO_W"):
        # Minimal logging for Pi Zero W
        logging.basicConfig(
            level=getattr(logging, level.upper()),
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler()]
        )
    else:
        # Full logging for development
        logging.basicConfig(
            level=getattr(logging, level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('info_ticker.log')
            ]
        )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Raspi Info Ticker v2.0 - E-ink Information Display System",
        epilog="The e-ink display is the primary output. Web interface is for management only."
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set logging level"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Display command (default and primary)
    display_parser = subparsers.add_parser(
        "display",
        help="Run e-ink display mode (primary operation)"
    )

    # Management command
    mgmt_parser = subparsers.add_parser(
        "management",
        help="Run web management interface only"
    )
    mgmt_parser.add_argument("--host", default="0.0.0.0", help="Server host")
    mgmt_parser.add_argument("--port", type=int, default=8080, help="Server port")

    # Preview command
    preview_parser = subparsers.add_parser(
        "preview",
        help="Generate a preview image"
    )
    preview_parser.add_argument("--plugin", required=True, help="Plugin to preview")
    preview_parser.add_argument("--output", help="Output file path")

    # Test command
    test_parser = subparsers.add_parser(
        "test",
        help="Test e-paper display"
    )
    test_parser.add_argument("--pattern", action="store_true", help="Display test pattern")

    # Plugins command
    plugins_parser = subparsers.add_parser(
        "plugins",
        help="List available plugins"
    )

    # Config command
    config_parser = subparsers.add_parser(
        "config",
        help="Create or validate configuration"
    )
    config_parser.add_argument("--output", help="Output file path")
    config_parser.add_argument("--validate", action="store_true", help="Validate existing config")

    args = parser.parse_args()

    # Import os here to avoid issues
    import os

    # Execute command
    if args.command == "display":
        run_display(args)
    elif args.command == "management":
        run_management(args)
    elif args.command == "preview":
        run_preview(args)
    elif args.command == "test":
        test_display(args)
    elif args.command == "plugins":
        list_plugins(args)
    elif args.command == "config":
        create_config(args)
    else:
        # Default to display mode
        print("Raspi Info Ticker v2.0")
        print("=" * 40)
        print("E-ink display is the primary output")
        print("Web interface is for management only")
        print()
        print("Usage:")
        print("  Display mode:  python src/main_v2.py display")
        print("  Management:    python src/main_v2.py management")
        print("  Test display:  python src/main_v2.py test --pattern")
        print()
        print("Starting display mode in 3 seconds...")

        import time
        time.sleep(3)
        args.command = "display"
        run_display(args)


if __name__ == "__main__":
    main()