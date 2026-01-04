# ===----------------------------------------------------------------------=== #
#
# This source file is part of the S.O.K open source project
#
# Copyright (c) 2026 S.O.K Team
# Licensed under the MIT License
#
# See LICENSE for license information
#
# ===----------------------------------------------------------------------=== #
"""
OAuth Providers - Authentication implementations for each service

To add a new provider:
1. Create a class inheriting from BaseOAuthProvider
2. Implement the authenticate() method
3. Register the provider in OAUTH_PROVIDERS
"""

import webbrowser
import time
from abc import ABC, abstractmethod
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Optional, Dict, Any
import requests

from sok.core.constants import SERVICE_SPOTIFY, SERVICE_IGDB
import base64
import secrets


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handles the OAuth callback"""

    callback_data = None

    def do_GET(self):
        """Receive the OAuth callback"""
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        OAuthCallbackHandler.callback_data = params

        # HTML response
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()

        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>S.O.K - Connection successful</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                    color: white;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                }
                .container {
                    text-align: center;
                    padding: 40px;
                    background: rgba(255,255,255,0.1);
                    border-radius: 16px;
                    backdrop-filter: blur(10px);
                }
                h1 { color: #50FA7B; margin-bottom: 10px; }
                p { color: #ccc; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Connection successful!</h1>
                <p>You can close this window and return to S.O.K</p>
            </div>
        </body>
        </html>
        """
        self.wfile.write(html.encode())

    def log_message(self, format, *args):
        """Suppress HTTP server logging.

        Args:
            format: Log message format.
            *args: Format arguments.
        """
        pass


class BaseOAuthProvider(ABC):
    """Base class for authentication providers"""

    def __init__(self, api_key: str, api_secret: str = "", port: int = 8765):
        """Initialize the OAuth provider.

        Args:
            api_key: API key or client ID.
            api_secret: API secret or client secret.
            port: Local port for OAuth callback server.
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.port = port
        self.callback_url = f"http://localhost:{port}/callback"

    @abstractmethod
    def authenticate(self) -> Optional[Dict[str, Any]]:
        """
        Perform authentication and return session data.

        Returns:
            Dict with session data (session_id, token, username, etc.)
            None if authentication is cancelled

        Raises:
            Exception if an error occurs
        """
        pass

    def _start_callback_server(self) -> HTTPServer:
        """Start a temporary server for the callback"""
        OAuthCallbackHandler.callback_data = None
        server = HTTPServer(("localhost", self.port), OAuthCallbackHandler)
        server.timeout = 120
        return server

    def _wait_for_callback(
        self, server: HTTPServer, timeout: int = 120
    ) -> Optional[dict]:
        """Wait for the OAuth callback"""
        start = time.time()
        while time.time() - start < timeout:
            server.handle_request()
            if OAuthCallbackHandler.callback_data:
                return OAuthCallbackHandler.callback_data
        return None


class SpotifyOAuthProvider(BaseOAuthProvider):
    """Spotify authentication provider"""

    def authenticate(self) -> Optional[Dict[str, Any]]:
        """Spotify authentication via OAuth 2.0"""
        if not self.api_key or not self.api_secret:
            raise Exception("Spotify Client ID and Client Secret are required")

        state = secrets.token_urlsafe(16)

        scopes = "user-read-private user-read-email user-library-read"

        auth_url = (
            f"https://accounts.spotify.com/authorize?"
            f"client_id={self.api_key}"
            f"&response_type=code"
            f"&redirect_uri={self.callback_url}"
            f"&scope={scopes}"
            f"&state={state}"
        )

        server = self._start_callback_server()
        webbrowser.open(auth_url)

        callback_data = self._wait_for_callback(server)
        server.server_close()

        if not callback_data or "code" not in callback_data:
            return None

        code = callback_data["code"][0]

        auth_header = base64.b64encode(
            f"{self.api_key}:{self.api_secret}".encode()
        ).decode()

        response = requests.post(
            "https://accounts.spotify.com/api/token",
            headers={
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.callback_url,
            },
            timeout=10,
        )

        if response.status_code != 200:
            raise Exception(f"Spotify error: {response.text}")

        token_data = response.json()
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")

        user_response = requests.get(
            "https://api.spotify.com/v1/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )

        username = ""
        if user_response.status_code == 200:
            user_data = user_response.json()
            username = user_data.get("display_name", user_data.get("id", ""))

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "username": username,
        }


class IGDBOAuthProvider(BaseOAuthProvider):
    """IGDB/Twitch authentication provider"""

    def authenticate(self) -> Optional[Dict[str, Any]]:
        """IGDB authentication via Twitch OAuth"""
        if not self.api_key or not self.api_secret:
            raise Exception("Twitch Client ID and Client Secret are required")

        response = requests.post(
            "https://id.twitch.tv/oauth2/token",
            params={
                "client_id": self.api_key,
                "client_secret": self.api_secret,
                "grant_type": "client_credentials",
            },
            timeout=10,
        )

        if response.status_code != 200:
            raise Exception(f"Twitch error: {response.text}")

        token_data = response.json()
        access_token = token_data.get("access_token")

        return {"access_token": access_token, "client_id": self.api_key}


OAUTH_PROVIDERS: Dict[str, type] = {
    SERVICE_SPOTIFY: SpotifyOAuthProvider,
    SERVICE_IGDB: IGDBOAuthProvider,
}


def get_oauth_provider(
    service_id: str, api_key: str, api_secret: str = ""
) -> Optional[BaseOAuthProvider]:
    """
    Get an OAuth provider instance for a service.

    Args:
        service_id: Service ID (tmdb, lastfm, etc.)
        api_key: Service API key
        api_secret: API secret if required

    Returns:
        Provider instance or None if not found
    """
    provider_class = OAUTH_PROVIDERS.get(service_id)
    if provider_class:
        return provider_class(api_key, api_secret)
    return None
