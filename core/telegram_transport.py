"""
Telegram transport interface.

Responsibility:
    Define the transport contract used by TelegramAlertManager.

The implementation is intentionally separated from message
generation and alert selection.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class TelegramTransport(ABC):
    """
    Abstract Telegram transport.
    """

    @abstractmethod
    async def send_message(
        self,
        message: str,
    ) -> None:
        """
        Send one Telegram message.
        """
        raise NotImplementedError

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
