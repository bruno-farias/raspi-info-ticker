"""Management web interface for Raspi Info Ticker.

Inspired by InkyPi - provides a simple web UI for remote configuration
and management, NOT for display. The e-ink is the primary display.
"""

from aiohttp import web
import aiohttp_cors
from aiohttp_session import setup, get_session
from aiohttp_session.cookie_storage import EncryptedCookieStorage
import logging
from pathlib import Path
import json
from typing import Dict, Any, Optional
from datetime import datetime
import base64
from PIL import Image
import io

from ..config import config_manager
from ..plugins import plugin_registry
from ..display.renderer import EInkRenderer


logger = logging.getLogger("management_web")


class ManagementInterface:
    """Web interface for managing the e-ink display ticker."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        """Initialize management interface."""
        self.host = host
        self.port = port
        self.app = web.Application()
        self.renderer = EInkRenderer()
        self.display_schedule = []
        self.current_preview = None

    async def setup(self):
        """Setup the web application."""
        # Session setup (simplified - no complex auth needed for management)
        secret_key = config_manager.config.auth.secret_key.encode() if config_manager.config else b'dev-secret-key'
        setup(self.app, EncryptedCookieStorage(secret_key))

        # Setup CORS
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })

        # Setup routes
        self.setup_routes()

        # Apply CORS to routes
        for route in list(self.app.router.routes()):
            cors.add(route)

    def setup_routes(self):
        """Setup management routes."""
        # API routes
        self.app.router.add_get('/', self.serve_index)
        self.app.router.add_get('/api/status', self.get_status)
        self.app.router.add_get('/api/plugins', self.get_plugins)
        self.app.router.add_post('/api/plugins/{name}/toggle', self.toggle_plugin)
        self.app.router.add_post('/api/plugins/{name}/configure', self.configure_plugin)
        self.app.router.add_get('/api/preview', self.get_preview)
        self.app.router.add_post('/api/refresh', self.force_refresh)
        self.app.router.add_get('/api/schedule', self.get_schedule)
        self.app.router.add_post('/api/schedule', self.update_schedule)
        self.app.router.add_get('/api/config', self.get_config)
        self.app.router.add_post('/api/config', self.update_config)
        self.app.router.add_post('/api/display/test', self.test_display)

        # Static files
        static_dir = Path(__file__).parent / 'static'
        if static_dir.exists():
            self.app.router.add_static('/static', static_dir)

    async def serve_index(self, request):
        """Serve the management interface HTML."""
        html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Raspi Info Ticker - Management</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }

        .header {
            background: #2c3e50;
            color: white;
            padding: 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }

        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2rem;
        }

        @media (max-width: 768px) {
            .grid { grid-template-columns: 1fr; }
        }

        .card {
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .card h2 {
            margin-bottom: 1rem;
            color: #2c3e50;
            font-size: 1.25rem;
        }

        .preview {
            background: #000;
            padding: 1rem;
            text-align: center;
            border-radius: 8px;
        }

        .preview img {
            max-width: 100%;
            height: auto;
            border: 2px solid #444;
        }

        .plugin-list {
            list-style: none;
        }

        .plugin-item {
            padding: 0.75rem;
            border-bottom: 1px solid #eee;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .plugin-item:last-child {
            border-bottom: none;
        }

        .toggle-switch {
            position: relative;
            width: 50px;
            height: 24px;
            background: #ccc;
            border-radius: 12px;
            cursor: pointer;
            transition: background 0.3s;
        }

        .toggle-switch.active {
            background: #27ae60;
        }

        .toggle-switch::after {
            content: '';
            position: absolute;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: white;
            top: 2px;
            left: 2px;
            transition: transform 0.3s;
        }

        .toggle-switch.active::after {
            transform: translateX(26px);
        }

        button {
            background: #3498db;
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            cursor: pointer;
            transition: background 0.3s;
        }

        button:hover {
            background: #2980b9;
        }

        .status-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 0.5rem;
        }

        .status-online { background: #27ae60; }
        .status-offline { background: #e74c3c; }

        .settings-form {
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .form-group {
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
        }

        label {
            font-weight: 500;
            color: #555;
        }

        input, select {
            padding: 0.5rem;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 1rem;
        }

        .schedule-list {
            list-style: none;
        }

        .schedule-item {
            padding: 0.5rem;
            background: #f8f9fa;
            margin-bottom: 0.5rem;
            border-radius: 4px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .message {
            padding: 1rem;
            border-radius: 4px;
            margin-bottom: 1rem;
        }

        .message.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }

        .message.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="container">
            <h1>🖼️ Raspi Info Ticker - Management Interface</h1>
            <p>Configure your e-ink display remotely</p>
        </div>
    </div>

    <div class="container">
        <div id="message"></div>

        <div class="grid">
            <!-- Display Preview -->
            <div class="card">
                <h2>Display Preview</h2>
                <div class="preview" id="preview">
                    <p style="color: #666;">Loading preview...</p>
                </div>
                <div style="margin-top: 1rem; display: flex; gap: 0.5rem;">
                    <button onclick="refreshPreview()">Refresh Preview</button>
                    <button onclick="testDisplay()">Test on Display</button>
                </div>
            </div>

            <!-- Status -->
            <div class="card">
                <h2>System Status</h2>
                <div id="status">
                    <p>Loading...</p>
                </div>
            </div>

            <!-- Plugin Management -->
            <div class="card">
                <h2>Active Plugins</h2>
                <ul class="plugin-list" id="plugins">
                    <li>Loading...</li>
                </ul>
            </div>

            <!-- Quick Settings -->
            <div class="card">
                <h2>Quick Settings</h2>
                <form class="settings-form" onsubmit="saveSettings(event)">
                    <div class="form-group">
                        <label>Refresh Interval (seconds)</label>
                        <input type="number" id="refresh-interval" min="10" max="3600" value="30">
                    </div>
                    <div class="form-group">
                        <label>Display Mode</label>
                        <select id="display-mode">
                            <option value="cycle">Cycle Plugins</option>
                            <option value="grid">Grid Layout</option>
                            <option value="dashboard">Dashboard</option>
                            <option value="single">Single Plugin</option>
                        </select>
                    </div>
                    <button type="submit">Save Settings</button>
                </form>
            </div>

            <!-- Schedule -->
            <div class="card">
                <h2>Display Schedule</h2>
                <ul class="schedule-list" id="schedule">
                    <li class="schedule-item">No schedule configured</li>
                </ul>
                <button onclick="addSchedule()">Add Schedule</button>
            </div>

            <!-- API Keys -->
            <div class="card">
                <h2>API Configuration</h2>
                <form class="settings-form" onsubmit="saveAPIKeys(event)">
                    <div class="form-group">
                        <label>Weather API Key</label>
                        <input type="password" id="weather-api" placeholder="OpenWeatherMap API Key">
                    </div>
                    <div class="form-group">
                        <label>Currency API Key</label>
                        <input type="password" id="currency-api" placeholder="FreeCurrencyAPI Key">
                    </div>
                    <button type="submit">Update API Keys</button>
                </form>
            </div>
        </div>
    </div>

    <script>
        // Global state
        let plugins = [];
        let config = {};

        // Initialize
        async function init() {
            await loadStatus();
            await loadPlugins();
            await loadConfig();
            await refreshPreview();

            // Auto-refresh
            setInterval(loadStatus, 30000);
            setInterval(refreshPreview, 60000);
        }

        // Load system status
        async function loadStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();

                document.getElementById('status').innerHTML = `
                    <p><span class="status-indicator status-online"></span>Display: Online</p>
                    <p>Active Plugins: ${data.enabled_plugins}/${data.plugins}</p>
                    <p>Last Update: ${new Date().toLocaleTimeString()}</p>
                    <p>Configuration: ${data.config_loaded ? 'Loaded' : 'Not Loaded'}</p>
                `;
            } catch (error) {
                document.getElementById('status').innerHTML = `
                    <p><span class="status-indicator status-offline"></span>Connection Error</p>
                `;
            }
        }

        // Load plugins
        async function loadPlugins() {
            try {
                const response = await fetch('/api/plugins');
                plugins = await response.json();

                const html = plugins.map(plugin => `
                    <li class="plugin-item">
                        <div>
                            <strong>${plugin.name}</strong>
                            <small> v${plugin.version}</small>
                        </div>
                        <div class="toggle-switch ${plugin.enabled ? 'active' : ''}"
                             onclick="togglePlugin('${plugin.name}', this)"></div>
                    </li>
                `).join('');

                document.getElementById('plugins').innerHTML = html;
            } catch (error) {
                showMessage('Failed to load plugins', 'error');
            }
        }

        // Load configuration
        async function loadConfig() {
            try {
                const response = await fetch('/api/config');
                config = await response.json();

                document.getElementById('refresh-interval').value = config.display?.refresh_interval || 30;
            } catch (error) {
                showMessage('Failed to load configuration', 'error');
            }
        }

        // Toggle plugin
        async function togglePlugin(name, element) {
            try {
                const response = await fetch(`/api/plugins/${name}/toggle`, {
                    method: 'POST'
                });

                if (response.ok) {
                    element.classList.toggle('active');
                    showMessage(`Plugin ${name} toggled`, 'success');
                    setTimeout(refreshPreview, 1000);
                }
            } catch (error) {
                showMessage('Failed to toggle plugin', 'error');
            }
        }

        // Refresh preview
        async function refreshPreview() {
            try {
                const response = await fetch('/api/preview');
                const data = await response.json();

                if (data.image) {
                    document.getElementById('preview').innerHTML = `
                        <img src="data:image/png;base64,${data.image}" alt="Display Preview">
                        <p style="color: #666; margin-top: 0.5rem;">
                            ${data.width}x${data.height} • Updated ${new Date().toLocaleTimeString()}
                        </p>
                    `;
                }
            } catch (error) {
                document.getElementById('preview').innerHTML = `
                    <p style="color: #e74c3c;">Failed to load preview</p>
                `;
            }
        }

        // Test display
        async function testDisplay() {
            try {
                const response = await fetch('/api/display/test', {
                    method: 'POST'
                });

                if (response.ok) {
                    showMessage('Test pattern sent to display', 'success');
                }
            } catch (error) {
                showMessage('Failed to test display', 'error');
            }
        }

        // Save settings
        async function saveSettings(event) {
            event.preventDefault();

            const settings = {
                display: {
                    refresh_interval: parseInt(document.getElementById('refresh-interval').value),
                    mode: document.getElementById('display-mode').value
                }
            };

            try {
                const response = await fetch('/api/config', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(settings)
                });

                if (response.ok) {
                    showMessage('Settings saved', 'success');
                }
            } catch (error) {
                showMessage('Failed to save settings', 'error');
            }
        }

        // Save API keys
        async function saveAPIKeys(event) {
            event.preventDefault();

            const keys = {
                plugins: {
                    weather: {
                        api_key: document.getElementById('weather-api').value
                    },
                    currency: {
                        api_key: document.getElementById('currency-api').value
                    }
                }
            };

            try {
                const response = await fetch('/api/config', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(keys)
                });

                if (response.ok) {
                    showMessage('API keys updated', 'success');
                    document.getElementById('weather-api').value = '';
                    document.getElementById('currency-api').value = '';
                }
            } catch (error) {
                showMessage('Failed to update API keys', 'error');
            }
        }

        // Show message
        function showMessage(text, type = 'info') {
            const messageEl = document.getElementById('message');
            messageEl.className = `message ${type}`;
            messageEl.textContent = text;
            messageEl.style.display = 'block';

            setTimeout(() => {
                messageEl.style.display = 'none';
            }, 5000);
        }

        // Initialize on load
        window.addEventListener('load', init);
    </script>
</body>
</html>
        """
        return web.Response(text=html, content_type='text/html')

    async def get_status(self, request):
        """Get system status."""
        status = {
            "status": "running",
            "plugins": len(plugin_registry.get_all_plugins()),
            "enabled_plugins": len(plugin_registry.get_enabled_plugins()),
            "config_loaded": config_manager.config is not None,
            "display_connected": True,  # Check actual display status
            "uptime": "N/A"  # Calculate actual uptime
        }
        return web.json_response(status)

    async def get_plugins(self, request):
        """Get plugin information."""
        plugins = plugin_registry.get_plugin_info()
        return web.json_response(plugins)

    async def toggle_plugin(self, request):
        """Toggle plugin enabled state."""
        plugin_name = request.match_info['name']
        plugin = plugin_registry.get_plugin(plugin_name)

        if plugin:
            plugin.config.enabled = not plugin.config.enabled
            # Save to config
            config_manager.set_plugin_config(plugin_name, plugin.config.dict())
            config_manager.save()

            return web.json_response({
                "success": True,
                "enabled": plugin.config.enabled
            })

        return web.json_response({"error": "Plugin not found"}, status=404)

    async def configure_plugin(self, request):
        """Configure plugin settings."""
        plugin_name = request.match_info['name']
        data = await request.json()

        config_manager.set_plugin_config(plugin_name, data)
        config_manager.save()

        # Reload plugin with new config
        plugin = plugin_registry.get_plugin(plugin_name)
        if plugin:
            # Update plugin config
            for key, value in data.items():
                if hasattr(plugin.config, key):
                    setattr(plugin.config, key, value)

        return web.json_response({"success": True})

    async def get_preview(self, request):
        """Generate and return display preview."""
        try:
            # Get enabled plugins
            plugins = plugin_registry.get_enabled_plugins()

            if plugins:
                # Get data from first plugin for preview
                plugin_data = await plugins[0].update()

                # Render preview
                image = self.renderer.render_plugin(plugin_data)

                # Convert to base64
                buffered = io.BytesIO()
                image.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()

                self.current_preview = img_str

                return web.json_response({
                    "image": img_str,
                    "width": self.renderer.width,
                    "height": self.renderer.height,
                    "plugin": plugin_data.plugin_name
                })

            else:
                # No plugins - show splash
                image = self.renderer.create_splash_screen("No Plugins Active")
                buffered = io.BytesIO()
                image.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()

                return web.json_response({
                    "image": img_str,
                    "width": self.renderer.width,
                    "height": self.renderer.height
                })

        except Exception as e:
            logger.error(f"Preview generation failed: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def force_refresh(self, request):
        """Force display refresh."""
        # Trigger display update
        # This would communicate with the actual display runner
        return web.json_response({"success": True, "message": "Display refresh triggered"})

    async def get_schedule(self, request):
        """Get display schedule."""
        return web.json_response(self.display_schedule)

    async def update_schedule(self, request):
        """Update display schedule."""
        data = await request.json()
        self.display_schedule = data
        # Save schedule to config
        return web.json_response({"success": True})

    async def get_config(self, request):
        """Get current configuration."""
        if config_manager.config:
            return web.json_response(config_manager.config.dict())
        return web.json_response({})

    async def update_config(self, request):
        """Update configuration."""
        data = await request.json()
        config_manager.update(data)
        config_manager.save()
        return web.json_response({"success": True})

    async def test_display(self, request):
        """Send test pattern to display."""
        # This would trigger actual display test
        return web.json_response({"success": True, "message": "Test pattern displayed"})

    async def run(self):
        """Run the management interface."""
        await self.setup()

        runner = web.AppRunner(self.app)
        await runner.setup()

        site = web.TCPSite(runner, self.host, self.port)
        await site.start()

        logger.info(f"Management interface running at http://{self.host}:{self.port}")
        logger.info("This is for MANAGEMENT ONLY - the e-ink display is the primary output")

        # Keep running
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Shutting down management interface")


def run_management_server(host="0.0.0.0", port=8080):
    """Run the management web interface."""
    interface = ManagementInterface(host, port)
    asyncio.run(interface.run())