"""
Rate limiter factory.

Responsibility:
    Creates an independent RateLimiter for each configured
    aggregator using the user's configuration.

Does NOT:
    - make HTTP requests;
    - know about Stage 1;
    - know about Stage 2;
    - decide which aggregator should be used;
    - manage request priority;
    - create aggregator adapters.
"""

from typing import Any

from aggregators.rate_limiter import RateLimiter


class RateLimiterFactory:
    """Creates rate limiters from aggregator configuration."""

    def create(
        self,
        config: dict[str, Any],
    ) -> dict[str, RateLimiter]:
        """
        Create one independent RateLimiter per aggregator.

        The configuration may contain either:
            - plain dictionaries;
            - Pydantic models exposing model_dump().

        Returns:
            Dictionary keyed by aggregator name.
        """

        if not isinstance(config, dict):
            raise TypeError(
                "Rate limiter configuration must be a dictionary."
            )

        limiters: dict[str, RateLimiter] = {}

        for aggregator_name, aggregator_config in config.items():

            normalized = self._normalize_config(
                aggregator_name,
                aggregator_config,
            )

            enabled = normalized.get(
                "enabled",
                True,
            )

            if not isinstance(enabled, bool):
                raise TypeError(
                    f"'enabled' for '{aggregator_name}' "
                    "must be a boolean."
                )

            if not enabled:
                continue

            rate_limit = normalized.get(
                "rate_limit"
            )

            if rate_limit is None:
                raise ValueError(
                    f"Rate-limit configuration is missing "
                    f"for '{aggregator_name}'."
                )

            rate_limit = self._normalize_rate_limit(
                aggregator_name,
                rate_limit,
            )

            limiter = RateLimiter(
                standard_interval=(
                    rate_limit["initial_delay_seconds"]
                ),
                max_interval=(
                    rate_limit["max_delay_seconds"]
                ),
                backoff_multiplier=(
                    rate_limit["delay_multiplier"]
                ),
                requests_per_minute=(
                    rate_limit["requests_per_minute"]
                ),
            )

            limiters[aggregator_name] = limiter

        return limiters

    @staticmethod
    def _normalize_config(
        aggregator_name: str,
        config: Any,
    ) -> dict[str, Any]:
        """Normalize an aggregator configuration."""

        if isinstance(config, dict):
            return config

        model_dump = getattr(
            config,
            "model_dump",
            None,
        )

        if callable(model_dump):
            normalized = model_dump()

            if isinstance(normalized, dict):
                return normalized

        raise TypeError(
            f"Configuration for '{aggregator_name}' "
            "must be a dictionary or a Pydantic "
            "model with model_dump()."
        )

    @staticmethod
    def _normalize_rate_limit(
        aggregator_name: str,
        rate_limit: Any,
    ) -> dict[str, Any]:
        """Normalize a rate-limit configuration."""

        if isinstance(rate_limit, dict):
            return rate_limit

        model_dump = getattr(
            rate_limit,
            "model_dump",
            None,
        )

        if callable(model_dump):
            normalized = model_dump()

            if isinstance(normalized, dict):
                return normalized

        raise TypeError(
            f"Rate-limit configuration for "
            f"'{aggregator_name}' must be a dictionary "
            "or a Pydantic model with model_dump()."
        )

    def create_one(
        self,
        aggregator_name: str,
        config: Any,
    ) -> RateLimiter:
        """
        Create a limiter for one aggregator.

        This method is useful when a component needs only
        one specific aggregator limiter.
        """

        normalized = self._normalize_config(
            aggregator_name,
            config,
        )

        enabled = normalized.get(
            "enabled",
            True,
        )

        if not isinstance(enabled, bool):
            raise TypeError(
                f"'enabled' for '{aggregator_name}' "
                "must be a boolean."
            )

        if not enabled:
            raise ValueError(
                f"Aggregator '{aggregator_name}' "
                "is disabled."
            )

        rate_limit = normalized.get(
            "rate_limit"
        )

        if rate_limit is None:
            raise ValueError(
                f"Rate-limit configuration is missing "
                f"for '{aggregator_name}'."
            )

        rate_limit = self._normalize_rate_limit(
            aggregator_name,
            rate_limit,
        )

        return RateLimiter(
            standard_interval=(
                rate_limit["initial_delay_seconds"]
            ),
            max_interval=(
                rate_limit["max_delay_seconds"]
            ),
            backoff_multiplier=(
                rate_limit["delay_multiplier"]
            ),
            requests_per_minute=(
                rate_limit["requests_per_minute"]
            ),
        )
