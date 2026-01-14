"""Web server for the info ticker using textual-serve."""

import asyncio
import logging
from pathlib import Path
from typing import Optional
import ssl

from textual_serve import Server
from aiohttp import web
from aiohttp_session import setup as setup_session
from aiohttp_session.cookie_storage import EncryptedCookieStorage
import aiohttp_cors

from ..tui.app import InfoTickerApp
from ..config import config_manager
from .auth import setup_auth, require_auth


logger = logging.getLogger(__name__)


class InfoTickerWebServer:
    """Web server for the info ticker application."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080,
                 ssl_cert: Optional[str] = None, ssl_key: Optional[str] = None):
        """Initialize web server."""
        self.host = host
        self.port = port
        self.ssl_cert = ssl_cert
        self.ssl_key = ssl_key
        self.app = web.Application()
        self.textual_server = None
        self.config = config_manager.load()

    async def setup(self):
        """Setup the web server."""
        # Setup session middleware
        secret_key = self.config.auth.secret_key.encode() if self.config.auth.secret_key else b'default-secret-key'
        setup_session(self.app, EncryptedCookieStorage(secret_key))

        # Setup authentication if enabled
        if self.config.auth.provider != "none":
            setup_auth(self.app, self.config.auth)

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

        # Setup Textual serve
        await self.setup_textual_serve()

        # Apply CORS to all routes
        for route in list(self.app.router.routes()):
            if not isinstance(route.resource, web.StaticResource):
                cors.add(route)

    def setup_routes(self):
        """Setup web routes."""
        # API routes
        self.app.router.add_get('/api/status', self.handle_status)
        self.app.router.add_get('/api/plugins', self.handle_plugins)
        self.app.router.add_get('/api/config', self.handle_get_config)
        self.app.router.add_post('/api/config', self.handle_update_config)
        self.app.router.add_post('/api/plugin/{name}/action', self.handle_plugin_action)

        # Authentication routes
        self.app.router.add_post('/auth/login', self.handle_login)
        self.app.router.add_post('/auth/logout', self.handle_logout)
        self.app.router.add_get('/auth/me', self.handle_me)

        # Static files (if needed)
        static_dir = Path(__file__).parent / 'static'
        if static_dir.exists():
            self.app.router.add_static('/', static_dir, name='static')

    async def setup_textual_serve(self):
        """Setup textual-serve for the TUI."""
        # Create Textual app instance
        tui_app = InfoTickerApp()

        # Create textual-serve server
        self.textual_server = Server(tui_app)

        # Add textual-serve routes to our app
        self.app.router.add_get('/terminal', self.handle_terminal)
        self.app.router.add_get('/ws', self.handle_websocket)

    async def handle_terminal(self, request):
        """Handle terminal page request."""
        # Check authentication if required
        if self.config.auth.provider != "none":
            if not await self.check_auth(request):
                return web.Response(status=401, text="Unauthorized")

        # Return the terminal HTML page
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Raspi Info Ticker - Terminal</title>
            <style>
                body {
                    margin: 0;
                    padding: 0;
                    background: #1e1e1e;
                    color: #ffffff;
                    font-family: 'Cascadia Code', 'Consolas', monospace;
                    overflow: hidden;
                }
                #terminal-container {
                    width: 100vw;
                    height: 100vh;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                }
                #terminal {
                    width: 100%;
                    height: 100%;
                }
                .auth-header {
                    position: fixed;
                    top: 0;
                    right: 0;
                    padding: 10px;
                    background: rgba(0, 0, 0, 0.5);
                    z-index: 1000;
                }
                .auth-header button {
                    background: #007bff;
                    color: white;
                    border: none;
                    padding: 5px 15px;
                    border-radius: 3px;
                    cursor: pointer;
                }
                .auth-header button:hover {
                    background: #0056b3;
                }
            </style>
        </head>
        <body>
            <div class="auth-header">
                <span id="username"></span>
                <button onclick="logout()">Logout</button>
            </div>
            <div id="terminal-container">
                <div id="terminal"></div>
            </div>
            <script src="https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.min.js"></script>
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.css" />
            <script>
                // Initialize terminal
                const term = new Terminal({
                    cursorBlink: true,
                    fontSize: 14,
                    fontFamily: 'Cascadia Code, Consolas, monospace',
                    theme: {
                        background: '#1e1e1e',
                        foreground: '#ffffff'
                    }
                });

                term.open(document.getElementById('terminal'));
                term.write('Connecting to Raspi Info Ticker...\\r\\n');

                // Connect WebSocket
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

                ws.onopen = () => {
                    term.write('Connected! Loading interface...\\r\\n');
                };

                ws.onmessage = (event) => {
                    // Handle textual-serve messages
                    const data = JSON.parse(event.data);
                    if (data.type === 'output') {
                        term.write(data.text);
                    }
                };

                ws.onerror = (error) => {
                    term.write(`\\r\\nConnection error: ${error}\\r\\n`);
                };

                ws.onclose = () => {
                    term.write('\\r\\nConnection closed.\\r\\n');
                };

                // Send terminal input to server
                term.onData((data) => {
                    if (ws.readyState === WebSocket.OPEN) {
                        ws.send(JSON.stringify({type: 'input', data: data}));
                    }
                });

                // Handle window resize
                window.addEventListener('resize', () => {
                    term.fit();
                    if (ws.readyState === WebSocket.OPEN) {
                        ws.send(JSON.stringify({
                            type: 'resize',
                            cols: term.cols,
                            rows: term.rows
                        }));
                    }
                });

                // Authentication functions
                async function checkAuth() {
                    try {
                        const response = await fetch('/auth/me');
                        if (response.ok) {
                            const data = await response.json();
                            document.getElementById('username').textContent = data.username || 'User';
                        }
                    } catch (error) {
                        console.error('Auth check failed:', error);
                    }
                }

                async function logout() {
                    try {
                        await fetch('/auth/logout', {method: 'POST'});
                        window.location.reload();
                    } catch (error) {
                        console.error('Logout failed:', error);
                    }
                }

                // Check authentication on load
                checkAuth();
            </script>
        </body>
        </html>
        """
        return web.Response(text=html, content_type='text/html')

    async def handle_websocket(self, request):
        """Handle WebSocket connection for textual-serve."""
        # Check authentication if required
        if self.config.auth.provider != "none":
            if not await self.check_auth(request):
                return web.Response(status=401, text="Unauthorized")

        # Let textual-serve handle the WebSocket
        if self.textual_server:
            return await self.textual_server.handle_websocket(request)
        else:
            return web.Response(status=503, text="Textual server not initialized")

    @require_auth
    async def handle_status(self, request):
        """Get application status."""
        from ..plugins import plugin_registry

        status = {
            "status": "running",
            "plugins": len(plugin_registry.get_all_plugins()),
            "enabled_plugins": len(plugin_registry.get_enabled_plugins()),
            "config_loaded": config_manager.config is not None
        }
        return web.json_response(status)

    @require_auth
    async def handle_plugins(self, request):
        """Get plugin information."""
        from ..plugins import plugin_registry

        plugins = plugin_registry.get_plugin_info()
        return web.json_response(plugins)

    @require_auth
    async def handle_get_config(self, request):
        """Get current configuration."""
        if config_manager.config:
            return web.json_response(config_manager.config.dict())
        return web.json_response({"error": "Configuration not loaded"}, status=500)

    @require_auth
    async def handle_update_config(self, request):
        """Update configuration."""
        try:
            data = await request.json()
            config_manager.update(data)
            config_manager.save()
            return web.json_response({"success": True, "message": "Configuration updated"})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

    @require_auth
    async def handle_plugin_action(self, request):
        """Handle plugin action."""
        from ..plugins import plugin_registry

        plugin_name = request.match_info['name']
        plugin = plugin_registry.get_plugin(plugin_name)

        if not plugin:
            return web.json_response({"error": "Plugin not found"}, status=404)

        if not plugin.supports_interaction():
            return web.json_response({"error": "Plugin does not support interaction"}, status=400)

        try:
            data = await request.json()
            action = data.get('action')
            params = data.get('params', {})

            result = await plugin.handle_interaction(action, params)
            return web.json_response(result)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

    async def handle_login(self, request):
        """Handle login request."""
        from .auth import authenticate_user

        try:
            data = await request.json()
            username = data.get('username')
            password = data.get('password')

            user = await authenticate_user(username, password, self.config.auth)
            if user:
                # Store user in session
                session = await get_session(request)
                session['user'] = user
                return web.json_response({"success": True, "user": user})
            else:
                return web.json_response({"error": "Invalid credentials"}, status=401)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

    async def handle_logout(self, request):
        """Handle logout request."""
        from aiohttp_session import get_session

        session = await get_session(request)
        session.clear()
        return web.json_response({"success": True})

    async def handle_me(self, request):
        """Get current user information."""
        from aiohttp_session import get_session

        session = await get_session(request)
        user = session.get('user')
        if user:
            return web.json_response(user)
        return web.json_response({"error": "Not authenticated"}, status=401)

    async def check_auth(self, request):
        """Check if request is authenticated."""
        from aiohttp_session import get_session

        if self.config.auth.provider == "none":
            return True

        session = await get_session(request)
        return 'user' in session

    async def run(self):
        """Run the web server."""
        await self.setup()

        # Setup SSL if configured
        ssl_context = None
        if self.ssl_cert and self.ssl_key:
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(self.ssl_cert, self.ssl_key)

        # Start the server
        runner = web.AppRunner(self.app)
        await runner.setup()

        site = web.TCPSite(runner, self.host, self.port, ssl_context=ssl_context)
        await site.start()

        protocol = "https" if ssl_context else "http"
        logger.info(f"Web server running at {protocol}://{self.host}:{self.port}")
        logger.info(f"Terminal interface at {protocol}://{self.host}:{self.port}/terminal")

        # Keep running
        await asyncio.Event().wait()


def run_server(host: str = "0.0.0.0", port: int = 8080,
               ssl_cert: Optional[str] = None, ssl_key: Optional[str] = None):
    """Run the web server."""
    server = InfoTickerWebServer(host, port, ssl_cert, ssl_key)
    asyncio.run(server.run())


if __name__ == "__main__":
    run_server()