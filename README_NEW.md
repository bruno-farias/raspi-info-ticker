# Raspi Info Ticker v2.0 - Modern Plugin-Based Architecture

A modular, extensible information display system for Raspberry Pi with support for e-paper displays, terminal UI (TUI), and web interfaces.

## Features

✅ **Plugin-Based Architecture** - Easily extend with custom data sources
✅ **Multiple Interfaces** - E-paper display, Textual TUI, and web interface
✅ **Web Configuration** - Configure remotely via browser with textual-serve
✅ **Multi-City Weather** - Select and cycle through multiple cities
✅ **Customizable Currency Pairs** - Choose any currency combinations
✅ **Authentication System** - Secure web access with 1Password compatibility (OAuth/OIDC)
✅ **Flexible Layouts** - Customize widget placement and appearance
✅ **Real-Time Updates** - Live data refresh with configurable intervals

## Installation

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Create configuration:**
```bash
cp config/config.example.yaml config/config.yaml
# Edit config/config.yaml with your API keys and preferences
```

3. **Generate initial config (optional):**
```bash
python src/main.py config
```

## Usage

### 1. Terminal UI (TUI)

Run the interactive terminal interface:
```bash
python src/main.py tui
```

**Keyboard shortcuts:**
- `q` - Quit
- `d` - Dashboard view
- `c` - Configuration view
- `r` - Refresh all plugins
- `s` - Save configuration
- `w` - Cycle weather cities
- `t` - Toggle theme

### 2. Web Interface

Start the web server with textual-serve:
```bash
python src/main.py web --port 8080
```

Access the interface:
- Terminal: http://localhost:8080/terminal
- API: http://localhost:8080/api/status

**With SSL:**
```bash
python src/main.py web --port 443 --ssl-cert cert.pem --ssl-key key.pem
```

### 3. E-Paper Display Mode

Run in headless mode for e-paper displays:
```bash
python src/main.py display
```

### 4. List Available Plugins

```bash
python src/main.py plugins
```

## Configuration

### Basic Configuration

Edit `config/config.yaml`:

```yaml
# Authentication
auth:
  provider: "basic"  # Options: none, basic, oauth, oidc
  username: "admin"
  secret_key: "your-secure-secret-key"

# Web server
web_server:
  enabled: true
  host: "0.0.0.0"
  port: 8080

# Display settings
display:
  mode: "all"
  refresh_interval: 15  # seconds
```

### Plugin Configuration

#### Weather Plugin
```yaml
plugins:
  weather:
    enabled: true
    api_key: "YOUR_OPENWEATHERMAP_API_KEY"
    cities:
      - name: "London"
        country: "UK"
      - name: "New York"
        state: "NY"
        country: "US"
    units: "metric"
```

#### Currency Plugin
```yaml
plugins:
  currency:
    enabled: true
    api_key: "YOUR_FREECURRENCYAPI_KEY"
    base_currency: "USD"
    target_currencies:
      - "EUR"
      - "GBP"
      - "JPY"
      - "BRL"
```

#### Crypto Plugin
```yaml
plugins:
  crypto:
    enabled: true
    provider: "coingecko"
    cryptocurrencies:
      - "bitcoin"
      - "ethereum"
    vs_currencies:
      - "usd"
      - "eur"
```

## Creating Custom Plugins

1. **Create a new plugin file** in `src/plugins/`:

```python
# src/plugins/my_plugin.py
from typing import Dict, Any
from .base import BasePlugin, PluginConfig

class MyPluginConfig(PluginConfig):
    api_key: str = ""
    custom_setting: str = "default"

class MyPlugin(BasePlugin):
    name = "my_plugin"
    version = "1.0.0"
    description = "My Custom Plugin"
    author = "Your Name"

    def get_config_schema(self):
        return MyPluginConfig

    async def fetch_data(self) -> Dict[str, Any]:
        # Fetch your data here
        return {"value": 42}

    def get_display_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Format data for display
        return {"formatted_value": f"Value: {data['value']}"}
```

2. **Register in configuration**:

```yaml
plugins:
  custom:
    my_plugin:
      enabled: true
      api_key: "your-key"
      custom_setting: "custom-value"
```

## API Endpoints

When running the web server, these endpoints are available:

- `GET /api/status` - Application status
- `GET /api/plugins` - List all plugins
- `GET /api/config` - Get configuration
- `POST /api/config` - Update configuration
- `POST /api/plugin/{name}/action` - Execute plugin action
- `POST /auth/login` - Login
- `POST /auth/logout` - Logout
- `GET /auth/me` - Current user info

## Authentication

### Basic Authentication

1. Set username and password:
```bash
python -c "from src.web.auth import hash_password; print(hash_password('your_password'))"
```

2. Update config.yaml:
```yaml
auth:
  provider: "basic"
  username: "admin"
  password_hash: "<generated_hash>"
```

### OAuth/OIDC (1Password Compatible)

Configure OAuth/OIDC in config.yaml:
```yaml
auth:
  provider: "oidc"
  client_id: "your-client-id"
  client_secret: "your-client-secret"
  authorization_url: "https://provider.com/auth"
  token_url: "https://provider.com/token"
  userinfo_url: "https://provider.com/userinfo"
```

## Remote Access via SSH

1. **SSH to your Raspberry Pi:**
```bash
ssh pi@raspberrypi.local
```

2. **Run TUI over SSH:**
```bash
python src/main.py tui
```

3. **Or use web interface:**
```bash
python src/main.py web --host 0.0.0.0
# Access from browser: http://raspberrypi.local:8080
```

## Docker Support (Optional)

Build and run with Docker:

```bash
# Build image
docker build -t raspi-info-ticker .

# Run container
docker run -d \
  -p 8080:8080 \
  -v ./config:/app/config \
  -v ./data:/app/data \
  --name info-ticker \
  raspi-info-ticker
```

## Troubleshooting

### API Keys
- OpenWeatherMap: https://openweathermap.org/api
- FreeCurrencyAPI: https://freecurrencyapi.com/
- CoinGecko: https://www.coingecko.com/api (free, no key required)

### Common Issues

1. **ImportError for textual or textual-serve:**
```bash
pip install textual textual-serve
```

2. **E-paper display not working:**
- Ensure SPI is enabled on Raspberry Pi
- Check waveshare_epd library installation

3. **Authentication issues:**
- Regenerate secret key
- Check password hash is correctly set

## Development

### Project Structure
```
raspi-info-ticker/
├── src/
│   ├── plugins/      # Plugin modules
│   ├── config/       # Configuration management
│   ├── tui/          # Textual TUI application
│   ├── web/          # Web server and API
│   └── display/      # E-paper display handler
├── config/           # Configuration files
├── data/             # Runtime data
└── cache/            # Cache directory
```

### Running Tests
```bash
pytest tests/
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your plugin or feature
4. Add tests
5. Submit a pull request

## License

MIT License - See LICENSE file for details

## Changelog

### v2.0.0
- Complete rewrite with plugin architecture
- Added Textual TUI interface
- Added web interface with textual-serve
- Implemented authentication system
- Added multi-city weather support
- Added customizable currency pairs
- Plugin system for extensibility
- Flexible layout system

### v1.0.0
- Initial release
- Basic e-paper display support
- Fixed weather, currency, and crypto displays