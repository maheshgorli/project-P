"""
OAuth2 token service for the Copernicus Data Space Ecosystem (CDSE).

Responsibilities
----------------
- Request a new access token using client_credentials grant
- Cache the token in memory until it is close to expiry
- Automatically refresh when the cached token has <= EXPIRY_BUFFER_SECONDS left
- Expose a clean dataclass (TokenResponse) for callers
- Raise AuthenticationError with actionable messages on every failure path

Thread-safety
-------------
A threading.Lock guards the cached state so concurrent FastAPI workers
do not race to refresh the token simultaneously.

Usage
-----
    from app.services.token_service import token_service, TokenResponse

    token: TokenResponse = token_service.get_token()
    # Use token.access_token in Authorization: Bearer <token> headers
"""

import logging
import threading
import time
from dataclasses import dataclass

import requests as _requests

from app.config import settings

logger = logging.getLogger(__name__)

# How many seconds before actual expiry we treat the token as expired.
# 60 s gives a comfortable window to swap the token before any in-flight
# Sentinel Hub request gets a 401.
_EXPIRY_BUFFER_SECONDS = 60


# ── Exceptions ───────────────────────────────────────────────────────────────

class AuthenticationError(Exception):
    """Raised when OAuth token acquisition or refresh fails."""


# ── Data model ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TokenResponse:
    """Immutable snapshot of a successfully obtained token."""

    access_token: str
    expires_in: int        # seconds until expiry as reported by the server
    token_type: str        # always "Bearer" for CDSE
    obtained_at: float     # time.monotonic() when this token was fetched

    @property
    def seconds_remaining(self) -> float:
        """How many seconds until this token should be considered expired."""
        age = time.monotonic() - self.obtained_at
        return self.expires_in - age

    @property
    def is_valid(self) -> bool:
        """True when the token still has more than EXPIRY_BUFFER_SECONDS left."""
        return self.seconds_remaining > _EXPIRY_BUFFER_SECONDS

    def redacted_summary(self) -> dict:
        """Safe dict for logging / API responses — never exposes the token value."""
        return {
            "access_token": self.access_token[:10] + "…[redacted]",
            "expires_in": self.expires_in,
            "token_type": self.token_type,
            "seconds_remaining": round(self.seconds_remaining),
        }


# ── Token service ─────────────────────────────────────────────────────────────

class _TokenService:
    """
    Singleton token manager.

    Call ``get_token()`` from any thread; the service handles caching and
    refresh transparently.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cached: TokenResponse | None = None

    # ── Public API ────────────────────────────────────────────────────────────

    def get_token(self) -> TokenResponse:
        """
        Return a valid access token, fetching a fresh one if necessary.

        Returns:
            TokenResponse with access_token, expires_in, token_type.

        Raises:
            AuthenticationError: on any network, HTTP, or credential error.
            EnvironmentError:    if SENTINEL_CLIENT_ID / SECRET are not set.
        """
        with self._lock:
            if self._cached is not None and self._cached.is_valid:
                logger.debug(
                    "Token cache hit — %d s remaining.",
                    round(self._cached.seconds_remaining),
                )
                return self._cached

            action = "Refreshing" if self._cached is not None else "Requesting"
            logger.info("%s CDSE OAuth token…", action)
            self._cached = self._fetch_token()
            logger.info(
                "Token obtained — type: %s, expires_in: %d s.",
                self._cached.token_type,
                self._cached.expires_in,
            )
            return self._cached

    def invalidate(self) -> None:
        """Force the next call to get_token() to request a fresh token."""
        with self._lock:
            self._cached = None
        logger.info("Token cache cleared.")

    @property
    def cached_token(self) -> TokenResponse | None:
        """Read-only access to the current cached token (may be None or expired)."""
        return self._cached

    # ── Internal ──────────────────────────────────────────────────────────────

    def _fetch_token(self) -> TokenResponse:
        """
        POST to the CDSE token endpoint and return a TokenResponse.

        Raises:
            AuthenticationError: on HTTP errors, missing fields, or network issues.
            EnvironmentError:    if credentials are not configured.
        """
        client_id     = settings.sentinel_client_id      # raises EnvironmentError if missing
        client_secret = settings.sentinel_client_secret  # raises EnvironmentError if missing

        payload = {
            "grant_type":    "client_credentials",
            "client_id":     client_id,
            "client_secret": client_secret,
        }

        logger.debug(
            "POST %s  [client_id prefix: %s…]",
            settings.SENTINEL_TOKEN_URL,
            client_id[:8],
        )

        obtained_at = time.monotonic()

        try:
            response = _requests.post(
                settings.SENTINEL_TOKEN_URL,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=15,
            )
        except _requests.Timeout:
            raise AuthenticationError(
                f"Token request timed out after 15 s "
                f"(endpoint: {settings.SENTINEL_TOKEN_URL})."
            )
        except _requests.ConnectionError as exc:
            raise AuthenticationError(
                f"Cannot reach token endpoint {settings.SENTINEL_TOKEN_URL}: {exc}"
            ) from exc
        except _requests.RequestException as exc:
            raise AuthenticationError(
                f"Unexpected network error during token request: {exc}"
            ) from exc

        # ── HTTP-level errors ─────────────────────────────────────────────────
        if response.status_code == 400:
            self._raise_oauth_error(response, "Bad request")
        elif response.status_code == 401:
            self._raise_oauth_error(response, "Invalid credentials")
        elif response.status_code == 403:
            self._raise_oauth_error(response, "Access forbidden — check account permissions")
        elif not response.ok:
            self._raise_oauth_error(response, f"HTTP {response.status_code}")

        # ── Parse body ────────────────────────────────────────────────────────
        try:
            body = response.json()
        except ValueError as exc:
            raise AuthenticationError(
                f"Token endpoint returned non-JSON body "
                f"(status {response.status_code}): {response.text[:200]}"
            ) from exc

        missing = [f for f in ("access_token", "expires_in", "token_type") if f not in body]
        if missing:
            raise AuthenticationError(
                f"Token response is missing expected fields: {missing}. "
                f"Got keys: {list(body.keys())}"
            )

        return TokenResponse(
            access_token=body["access_token"],
            expires_in=int(body["expires_in"]),
            token_type=body["token_type"],
            obtained_at=obtained_at,
        )

    @staticmethod
    def _raise_oauth_error(response: _requests.Response, label: str) -> None:
        """Parse an OAuth error body and raise AuthenticationError."""
        try:
            body = response.json()
            error       = body.get("error", "unknown_error")
            description = body.get("error_description", "No description provided.")
        except ValueError:
            error       = "parse_error"
            description = response.text[:300]

        raise AuthenticationError(
            f"OAuth token request failed — {label}.\n"
            f"  error:             {error}\n"
            f"  error_description: {description}\n"
            f"  endpoint:          {settings.SENTINEL_TOKEN_URL}\n"
            f"  Verify SENTINEL_CLIENT_ID and SENTINEL_CLIENT_SECRET in backend/.env"
        )


# ── Module-level singleton ────────────────────────────────────────────────────

#: Use this instance everywhere instead of constructing your own.
token_service = _TokenService()
