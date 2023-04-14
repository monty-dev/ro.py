"""

This module contains classes used internally by ro.py for sending requests to Roblox endpoints.

"""


from __future__ import annotations
import contextlib
from typing import Dict, Optional

from json import JSONDecodeError

from httpx import AsyncClient, Response

from .exceptions import get_exception_from_status_code
from ..utilities.url import URLGenerator

_xcsrf_allowed_methods: Dict[str, bool] = {"post": True, "put": True, "patch": True, "delete": True}


class Requests:
    """
    A special request object that implements special functionality required to connect to some Roblox endpoints.

    Attributes:
        session: Base session object to use when sending requests.
        xcsrf_token_name: The header that will contain the Cross-Site Request Forgery token.
        url_generator: URL generator for ban parsing.
    """

    def __init__(self, url_generator: URLGenerator = None, session: AsyncClient = None, xcsrf_token_name: str = "X-CSRF-Token"):
        """
        Arguments:
            session: A custom session object to use for sending requests, compatible with httpx.AsyncClient.
            xcsrf_token_name: The header to place X-CSRF-Token data into.
            url_generator: URL generator for ban parsing.
        """
        self._url_generator: Optional[URLGenerator] = url_generator
        self.session: AsyncClient

        self.session = AsyncClient() if session is None else session
        self.xcsrf_token_name: str = xcsrf_token_name

        self.session.headers["User-Agent"] = "Roblox/WinInet"
        self.session.headers["Referer"] = "www.roblox.com"

    async def request(self, method: str, *args, **kwargs) -> Response:
        """
        Arguments:
            method: The request method.

        Returns:
            An HTTP response.
        """

        handle_xcsrf_token = kwargs.pop("handle_xcsrf_token", True)
        skip_roblox = kwargs.pop("skip_roblox", False)

        response = await self.session.request(method, *args, **kwargs)

        if skip_roblox:
            return response

        method = method.lower()

        if handle_xcsrf_token and self.xcsrf_token_name in response.headers and _xcsrf_allowed_methods.get(method):
            self.session.headers[self.xcsrf_token_name] = response.headers[self.xcsrf_token_name]
            if response.status_code == 403:  # Request failed, send it again
                response = await self.session.request(method, *args, **kwargs)

        if kwargs.get("stream"):
            # Streamed responses should not be decoded, so we immediately return the response.
            return response

        if not response.is_error:
            return response
        # Something went wrong, parse an error
        content_type = response.headers.get("Content-Type")
        errors = None
        if content_type and content_type.startswith("application/json"):
            data = None
            with contextlib.suppress(JSONDecodeError):
                data = response.json()
            errors = data and data.get("errors")

        exception = get_exception_from_status_code(response.status_code)(response=response, errors=errors)
        raise exception

    async def get(self, *args, **kwargs) -> Response:
        """
        Sends a GET request.

        Returns:
            An HTTP response.
        """

        return await self.request("GET", *args, **kwargs)

    async def post(self, *args, **kwargs) -> Response:
        """
        Sends a POST request.

        Returns:
            An HTTP response.
        """

        return await self.request("POST", *args, **kwargs)

    async def put(self, *args, **kwargs) -> Response:
        """
        Sends a PATCH request.

        Returns:
            An HTTP response.
        """

        return await self.request("PUT", *args, **kwargs)

    async def patch(self, *args, **kwargs) -> Response:
        """
        Sends a PATCH request.

        Returns:
            An HTTP response.
        """

        return await self.request("PATCH", *args, **kwargs)

    async def delete(self, *args, **kwargs) -> Response:
        """
        Sends a DELETE request.

        Returns:
            An HTTP response.
        """

        return await self.request("DELETE", *args, **kwargs)
