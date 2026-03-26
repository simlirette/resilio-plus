import time
from abc import ABC, abstractmethod

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.schemas.connector import ConnectorCredential


class ConnectorError(Exception):
    def __init__(self, provider: str, message: str) -> None:
        super().__init__(message)
        self.provider = provider


class ConnectorAuthError(ConnectorError):
    pass


class ConnectorRateLimitError(ConnectorError):
    def __init__(self, provider: str, message: str, retry_after: int = 60) -> None:
        super().__init__(provider, message)
        self.retry_after = retry_after


class ConnectorAPIError(ConnectorError):
    def __init__(self, provider: str, message: str, status_code: int = 0) -> None:
        super().__init__(provider, message)
        self.status_code = status_code


class BaseConnector(ABC):
    provider: str
    _retry_wait = wait_exponential(multiplier=2, min=2, max=8)

    def __init__(
        self,
        credential: ConnectorCredential,
        client_id: str,
        client_secret: str,
    ) -> None:
        self.credential = credential
        self.client_id = client_id
        self.client_secret = client_secret
        self._client = httpx.Client(timeout=30.0)

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> "BaseConnector":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def get_valid_token(self) -> str:
        """Return a valid access token, refreshing proactively if expires in < 5 min."""
        expires_at = self.credential.expires_at
        if expires_at is not None and expires_at < (time.time() + 300):
            self.credential = self._do_refresh_token()
        return self.credential.access_token or ""

    @abstractmethod
    def _do_refresh_token(self) -> ConnectorCredential:
        """Provider-specific token refresh. Returns updated credential."""
        ...

    def _request(self, method: str, url: str, **kwargs: object) -> dict:
        """HTTP request with 3-attempt tenacity retry + 429/401 handling.

        NOTE: Uses inner-function closure pattern because @retry cannot be applied
        directly as a class decorator on instance methods — the decorator binds at
        class-definition time before any instance exists.

        429 raises ConnectorRateLimitError immediately (not retried) — caller backs off.
        401 raises ConnectorAuthError immediately (not retried).
        Other HTTP errors become ConnectorAPIError and ARE retried up to 3 times.
        """
        @retry(
            stop=stop_after_attempt(3),
            wait=self._retry_wait,
            retry=retry_if_exception_type((ConnectorAPIError, httpx.HTTPError)),
            reraise=True,
        )
        def _inner() -> dict:
            response = self._client.request(method, url, **kwargs)
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                raise ConnectorRateLimitError(
                    provider=self.provider,
                    message=f"Rate limited by {self.provider}",
                    retry_after=retry_after,
                )
            if response.status_code == 401:
                raise ConnectorAuthError(
                    provider=self.provider,
                    message=f"Authentication failed for {self.provider}",
                )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                raise ConnectorAPIError(
                    provider=self.provider,
                    message=str(e),
                    status_code=response.status_code,
                ) from e
            return response.json()

        return _inner()
