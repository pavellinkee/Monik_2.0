"""
Telegram transport factory.
"""

from __future__ import annotations

from config.runtime_config import RuntimeConfig
from integrations.telegram_transport import (
    TelegramBotTransport,
)


class TelegramTransportFactory:
    """
    Creates Telegram transport from runtime configuration.
    """

    def create(
        self,
        config: RuntimeConfig,
    ):
        """
        Create configured Telegram transport.

        Returns None when Telegram is disabled.
        """

        if not isinstance(
            config,
            RuntimeConfig,
        ):
            raise TypeError(
                "config must be a RuntimeConfig."
            )

        if not config.telegram_enabled:
            return None

        if not config.telegram_bot_token:
            raise ValueError(
                "Telegram is enabled but "
                "telegram_bot_token is missing."
            )

        if not config.telegram_chat_id:
            raise ValueError(
                "Telegram is enabled but "
                "telegram_chat_id is missing."
            )

        return TelegramBotTransport(
            bot_token=config.telegram_bot_token,
            chat_id=config.telegram_chat_id,
        )

    def build(
        self,
        config: RuntimeConfig,
    ):
        """
        Compatibility alias.
        """
        return self.create(config)
