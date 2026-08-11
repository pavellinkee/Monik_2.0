"""
Blockchain chain selector.

Responsibility:
    Determine which blockchain networks are actually available
    from the configured token resolver.

No chain IDs are hardcoded.

Compatibility:
    Supports both:
        resolve_enabled()
        get_enabled_tokens()
"""

from __future__ import annotations

from collections.abc import Iterable


class ChainSelector:
    """
    Discovers available blockchain networks from token data.
    """

    def __init__(
        self,
        token_resolver,
    ) -> None:
        if token_resolver is None:
            raise TypeError(
                "token_resolver is required."
            )

        self._token_resolver = (
            token_resolver
        )

    async def get_chain_ids(
        self,
    ) -> tuple[int, ...]:
        """
        Return unique available chain IDs.

        Only addresses marked as available are considered.
        """

        tokens = (
            await self._resolve_enabled_tokens()
        )

        chain_ids: set[int] = set()

        for token in tokens:
            addresses = getattr(
                token,
                "addresses",
                (),
            )

            for address in addresses:
                if not getattr(
                    address,
                    "availability",
                    False,
                ):
                    continue

                chain_id = int(
                    address.chain_id
                )

                if chain_id <= 0:
                    continue

                chain_ids.add(
                    chain_id
                )

        return tuple(
            sorted(chain_ids)
        )

    async def resolve(
        self,
    ) -> tuple[int, ...]:
        """
        Compatibility alias.
        """

        return await self.get_chain_ids()

    async def get_available_chains(
        self,
    ) -> tuple[int, ...]:
        """
        Compatibility alias.
        """

        return await self.get_chain_ids()

    async def _resolve_enabled_tokens(
        self,
    ) -> tuple:
        """
        Resolve enabled tokens through the newest interface first.
        """

        current = getattr(
            self._token_resolver,
            "resolve_enabled",
            None,
        )

        if callable(current):
            result = await current()

            return tuple(
                result
            )

        legacy = getattr(
            self._token_resolver,
            "get_enabled_tokens",
            None,
        )

        if callable(legacy):
            result = await legacy()

            return tuple(
                result
            )

        raise TypeError(
            "Token resolver does not provide either "
            "resolve_enabled() or get_enabled_tokens()."
        )
