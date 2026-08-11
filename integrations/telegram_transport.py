"""
Telegram Bot API transport.

Responsibility:
    Send messages through Telegram Bot API.

The transport does NOT:
    - choose opportunities;
    - calculate profitability;
    - format arbitrage results;
    - perform deduplication.
"""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from core.telegram_transport import (
    TelegramTransport,
)


class TelegramBotTransport(
    TelegramTransport
):
    """
    Minimal dependency-free Telegram Bot API transport.

    Uses Python standard library so the core scanner does not
    require a Telegram-specific SDK.
    """

    def __init__(
        self,
        *,
        bot_token: str,
        chat_id: str,
        timeout_seconds: float = 15.0,
    ) -> None:
        if not bot_token.strip():
            raise ValueError(
                "bot_token cannot be empty."
            )

        if not chat_id.strip():
            raise ValueError(
                "chat_id cannot be empty."
            )

        if timeout_seconds <= 0:
            raise ValueError(
                "timeout_seconds must be greater "
                "than zero."
            )

        self._bot_token = bot_token
        self._chat_id = chat_id
        self._timeout_seconds = timeout_seconds

    async def send_message(
        self,
        message: str,
    ) -> None:
        """
        Send one message through Telegram Bot API.
        """

        if not isinstance(
            message,
            str,
        ):
            raise TypeError(
                "message must be a string."
            )

        if not message.strip():
            raise ValueError(
                "message cannot be empty."
            )

        import asyncio

        await asyncio.to_thread(
            self._send_sync,
            message,
        )

    def _send_sync(
        self,
        message: str,
    ) -> None:
        url = (
            "https://api.telegram.org/"
            f"bot{self._bot_token}/sendMessage"
        )

        payload = json.dumps(
            {
                "chat_id": self._chat_id,
                "text": message,
            }
        ).encode("utf-8")

        request = Request(
            url,
            data=payload,
            headers={
                "Content-Type":
                    "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(
                request,
                timeout=self._timeout_seconds,
            ) as response:
                if response.status != 200:
                    raise RuntimeError(
                        "Telegram API returned HTTP "
                        f"{response.status}."
                    )

        except HTTPError as exc:
            raise RuntimeError(
                "Telegram API request failed with "
                f"HTTP {exc.code}."
            ) from exc

        except URLError as exc:
            raise RuntimeError(
                "Telegram API connection failed."
            ) from exc

    async def send(
        self,
        message: str,
    ) -> None:
        """
        Legacy compatibility alias.
        """

        await self.send_message(
            message
        )
