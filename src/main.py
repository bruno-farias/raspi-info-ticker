#!/usr/bin/env python3
"""Main entry point for the Raspi Info Ticker application."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import config_manager
from src.plugins import plugin_registry
from src.tui import run_app


def setup_logging(level: str = "INFO"):
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('info_ticker.log')
        ]
    )


def run_tui(args):
    """Run the Textual TUI application."""
    setup_logging(args.log_level)
    logging.info("Starting Info Ticker TUI...")
    run_app()


def run_web(args):
    """Run the web server with textual-serve."""
    setup_logging(args.log_level)
    logging.info("Starting Info Ticker Web Server...")

    from src.web.server import run_server
    run_server(
        host=args.host,
        port=args.port,
        ssl_cert=args.ssl_cert,
        ssl_key=args.ssl_key
    )


def run_display(args):
    """Run in e-paper display mode (headless)."""
    setup_logging(args.log_level)
    logging.info("Starting Info Ticker Display Mode...")

    from src.display.runner import DisplayRunner
    runner = DisplayRunner()
    asyncio.run(runner.run())


def create_config(args):
    """Create or update configuration file."""
    setup_logging(args.log_level)
    logging.info("Creating configuration...")

    # Load or create config
    config = config_manager.load(create_if_missing=True)

    # Save to specified path
    if args.output:
        config_manager.save(Path(args.output))
        print(f"Configuration saved to {args.output}")
    else:
        config_manager.save()
        print(f"Configuration saved to {config_manager.config_path}")


def list_plugins(args):
    """List available plugins."""
    setup_logging(args.log_level)

    # Discover plugins
    plugin_registry.discover_plugins()

    # Print plugin information
    print("\nAvailable Plugins:")
    print("-" * 60)

    for info in plugin_registry.get_plugin_info():
        print(f"Name:        {info['name']}")
        print(f"Version:     {info['version']}")
        print(f"Description: {info['description']}")
        print(f"Author:      {info['author']}")
        print("-" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Raspi Info Ticker - Modular information display system"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set logging level"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # TUI command
    tui_parser = subparsers.add_parser("tui", help="Run Textual TUI interface")

    # Web command
    web_parser = subparsers.add_parser("web", help="Run web interface with textual-serve")
    web_parser.add_argument("--host", default="0.0.0.0", help="Server host")
    web_parser.add_argument("--port", type=int, default=8080, help="Server port")
    web_parser.add_argument("--ssl-cert", help="SSL certificate file")
    web_parser.add_argument("--ssl-key", help="SSL key file")

    # Display command
    display_parser = subparsers.add_parser("display", help="Run in e-paper display mode")

    # Config command
    config_parser = subparsers.add_parser("config", help="Create or update configuration")
    config_parser.add_argument("--output", help="Output configuration file path")

    # Plugins command
    plugins_parser = subparsers.add_parser("plugins", help="List available plugins")

    args = parser.parse_args()

    # Execute command
    if args.command == "tui":
        run_tui(args)
    elif args.command == "web":
        run_web(args)
    elif args.command == "display":
        run_display(args)
    elif args.command == "config":
        create_config(args)
    elif args.command == "plugins":
        list_plugins(args)
    else:
        # Default to TUI
        run_tui(args)


if __name__ == "__main__":
    main()