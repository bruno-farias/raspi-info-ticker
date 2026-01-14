"""Authentication module for the web server."""

import logging
from typing import Optional, Dict, Any
from functools import wraps
import hashlib
import secrets
from datetime import datetime, timedelta

from aiohttp import web
from aiohttp_session import get_session
from passlib.context import CryptContext
from jose import jwt, JWTError

from ..config.schemas import AuthConfig, AuthProvider


logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


async def authenticate_user(username: str, password: str, auth_config: AuthConfig) -> Optional[Dict[str, Any]]:
    """Authenticate a user."""
    if auth_config.provider == AuthProvider.BASIC:
        # Basic authentication
        if username == auth_config.username:
            if auth_config.password_hash:
                if verify_password(password, auth_config.password_hash):
                    return {
                        "username": username,
                        "authenticated": True,
                        "provider": "basic"
                    }
            else:
                # For initial setup, allow if password matches username (insecure, for demo only)
                logger.warning("No password hash configured, using demo mode")
                if password == "admin":  # Demo password
                    return {
                        "username": username,
                        "authenticated": True,
                        "provider": "basic",
                        "demo_mode": True
                    }
        return None

    elif auth_config.provider == AuthProvider.OAUTH:
        # OAuth authentication (to be implemented)
        logger.warning("OAuth authentication not yet implemented")
        return None

    elif auth_config.provider == AuthProvider.OIDC:
        # OIDC authentication (to be implemented)
        logger.warning("OIDC authentication not yet implemented")
        return None

    else:
        # No authentication
        return {
            "username": "anonymous",
            "authenticated": True,
            "provider": "none"
        }


def create_access_token(data: dict, secret_key: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm="HS256")
    return encoded_jwt


def verify_token(token: str, secret_key: str) -> Optional[Dict[str, Any]]:
    """Verify a JWT token."""
    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        return payload
    except JWTError:
        return None


def require_auth(func):
    """Decorator to require authentication for a handler."""
    @wraps(func)
    async def wrapper(self, request):
        # Check if authentication is enabled
        if hasattr(self, 'config') and self.config.auth.provider == AuthProvider.NONE:
            return await func(self, request)

        # Check session
        session = await get_session(request)
        if 'user' not in session:
            # Check for Bearer token
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]
                if hasattr(self, 'config'):
                    payload = verify_token(token, self.config.auth.secret_key)
                    if payload:
                        session['user'] = payload
                    else:
                        return web.json_response({"error": "Invalid token"}, status=401)
                else:
                    return web.json_response({"error": "No configuration"}, status=500)
            else:
                return web.json_response({"error": "Authentication required"}, status=401)

        return await func(self, request)
    return wrapper


def setup_auth(app: web.Application, auth_config: AuthConfig):
    """Setup authentication for the application."""
    # Add authentication middleware
    @web.middleware
    async def auth_middleware(request, handler):
        # Skip authentication for certain paths
        skip_paths = ['/auth/login', '/auth/logout', '/health', '/']
        if request.path in skip_paths:
            return await handler(request)

        # Check if authentication is required
        if auth_config.provider != AuthProvider.NONE:
            session = await get_session(request)

            # Check session
            if 'user' not in session:
                # Check for API token in header
                auth_header = request.headers.get('Authorization', '')
                if auth_header.startswith('Bearer '):
                    token = auth_header[7:]
                    payload = verify_token(token, auth_config.secret_key)
                    if not payload:
                        # Allow OPTIONS requests for CORS
                        if request.method == 'OPTIONS':
                            return await handler(request)
                        return web.json_response({"error": "Invalid token"}, status=401)
                else:
                    # Allow OPTIONS requests for CORS
                    if request.method == 'OPTIONS':
                        return await handler(request)
                    # No authentication provided
                    if request.path.startswith('/api/'):
                        return web.json_response({"error": "Authentication required"}, status=401)

        return await handler(request)

    app.middlewares.append(auth_middleware)


class AuthManager:
    """Manager for authentication operations."""

    def __init__(self, auth_config: AuthConfig):
        """Initialize auth manager."""
        self.config = auth_config
        self.logger = logging.getLogger("auth_manager")

    def create_user(self, username: str, password: str) -> Dict[str, Any]:
        """Create a new user (for basic auth)."""
        return {
            "username": username,
            "password_hash": hash_password(password),
            "created_at": datetime.utcnow().isoformat()
        }

    def update_password(self, username: str, new_password: str) -> bool:
        """Update user password."""
        if self.config.provider == AuthProvider.BASIC:
            if username == self.config.username:
                self.config.password_hash = hash_password(new_password)
                return True
        return False

    async def setup_oauth(self) -> bool:
        """Setup OAuth provider."""
        # To be implemented with specific OAuth providers (Google, GitHub, etc.)
        self.logger.warning("OAuth setup not yet implemented")
        return False

    async def setup_oidc(self) -> bool:
        """Setup OIDC provider (for 1Password compatibility)."""
        # To be implemented with OIDC providers
        self.logger.warning("OIDC setup not yet implemented")
        return False

    def generate_api_token(self, user_data: Dict[str, Any]) -> str:
        """Generate an API token for a user."""
        return create_access_token(user_data, self.config.secret_key)

    def validate_api_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate an API token."""
        return verify_token(token, self.config.secret_key)


def create_demo_auth_config() -> AuthConfig:
    """Create a demo authentication configuration."""
    return AuthConfig(
        provider=AuthProvider.BASIC,
        secret_key=secrets.token_urlsafe(32),
        username="admin",
        password_hash=hash_password("admin")
    )


__all__ = [
    "hash_password",
    "verify_password",
    "authenticate_user",
    "create_access_token",
    "verify_token",
    "require_auth",
    "setup_auth",
    "AuthManager",
    "create_demo_auth_config"
]