"""
Aggregator engine.

Responsibility:
    Orchestrates quote requests between the scanner
    and configured aggregator adapters.

Architecture:

    Scanner / Stage
           |
           v
    AggregatorEngine
           |
           +----------------------+
           |                      |
           v                      v
    InstanceRegistry        QueuePool
           |                      |
           |               +------+------+
           |               |             |
           v               v             v
       Aggregator       1inch          0x
                        queue          queue
                           |             |
                           v             v
                       RateLimiter   RateLimiter

Does NOT:
    - calculate arbitrage;
    - calculate profitability;
    - calculate gas costs;
    - resolve tokens;
    - access the database;
    - send Telegram messages;
    - implement rate limiting;
    - implement failover;
    - decide Stage 1 or Stage 2 logic.

Stage priority is delegated to AggregatorRequestQueue.
Different aggregators may execute concurrently because
each aggregator has an independent queue.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable

from aggregators.aggregator_interface import (
    AggregatorInterface,
)
from aggregators.instance_registry import (
    AggregatorInstanceRegistry,
)
from aggregators.quote import Quote
from aggregators.quote_request import QuoteRequest
from aggregators.queue_pool import (
    AggregatorQueuePool,
)


class AggregatorEngine:
    """
    Orchestrates quote requests for configured aggregators.

    The engine is intentionally unaware of scanner strategy.
    The caller decides which aggregators to query and which
    stage the request belongs to.
    """

    def __init__(
        self,
        instances: AggregatorInstanceRegistry,
        queues: AggregatorQueuePool,
    ) -> None:
        if not isinstance(
            instances,
            AggregatorInstanceRegistry,
        ):
            raise TypeError(
                "instances must be an "
                "AggregatorInstanceRegistry."
            )

        if not isinstance(
            queues,
            AggregatorQueuePool,
        ):
            raise TypeError(
                "queues must be an "
                "AggregatorQueuePool."
            )

        self._instances = instances
        self._queues = queues

    async def get_quote(
        self,
        aggregator_name: str,
        request: QuoteRequest,
        stage: int,
    ) -> Quote:
        """
        Request one quote through the aggregator's queue.

        The queue is responsible for:
            - request ordering;
            - Stage 1 / Stage 2 priority;
            - rate limiter execution.

        The engine only connects the correct aggregator
        instance with the correct queue.
        """

        if not isinstance(
            aggregator_name,
            str,
        ):
            raise TypeError(
                "aggregator_name must be a string."
            )

        if not aggregator_name.strip():
            raise ValueError(
                "aggregator_name cannot be empty."
            )

        if not isinstance(
            request,
            QuoteRequest,
        ):
            raise TypeError(
                "request must be a QuoteRequest."
            )

        if stage not in (1, 2):
            raise ValueError(
                "stage must be 1 or 2."
            )

        aggregator = self._instances.get(
            aggregator_name
        )

        if aggregator is None:
            raise KeyError(
                f"Unknown configured aggregator: "
                f"'{aggregator_name}'."
            )

        queue = self._queues.get(
            aggregator_name
        )

        async def execute() -> Quote:
            result = await aggregator.get_quote(
                request
            )

            if not isinstance(
                result,
                Quote,
            ):
                raise TypeError(
                    f"Aggregator '{aggregator_name}' "
                    "returned an invalid quote."
                )

            return result

        return await queue.submit(
            execute,
            stage=stage,
        )

    async def get_quotes(
        self,
        aggregator_names: Iterable[str],
        request: QuoteRequest,
        stage: int,
    ) -> dict[str, Quote]:
        """
        Request quotes from multiple aggregators.

        Requests belonging to different aggregators are submitted
        concurrently. Each individual aggregator still uses its
        own queue, so requests to the same aggregator remain
        sequential.

        The returned dictionary contains results keyed by the
        aggregator name and preserves the order of the supplied
        aggregator_names.
        """

        if not isinstance(
            request,
            QuoteRequest,
        ):
            raise TypeError(
                "request must be a QuoteRequest."
            )

        if stage not in (1, 2):
            raise ValueError(
                "stage must be 1 or 2."
            )

        names = list(
            aggregator_names
        )

        if not names:
            raise ValueError(
                "At least one aggregator must "
                "be requested."
            )

        if len(set(names)) != len(names):
            raise ValueError(
                "Aggregator names must be unique."
            )

        for name in names:
            if not isinstance(
                name,
                str,
            ):
                raise TypeError(
                    "Each aggregator name must "
                    "be a string."
                )

            if not name.strip():
                raise ValueError(
                    "Aggregator names cannot be empty."
                )

        tasks = [
            self.get_quote(
                aggregator_name=name,
                request=request,
                stage=stage,
            )
            for name in names
        ]

        quotes = await asyncio.gather(
            *tasks
        )

        return {
            name: quote
            for name, quote in zip(
                names,
                quotes,
            )
        }

    def contains(
        self,
        aggregator_name: str,
    ) -> bool:
        """
        Return whether an aggregator is available
        in both the instance registry and queue pool.
        """

        return (
            self._instances.contains(
                aggregator_name
            )
            and self._queues.contains(
                aggregator_name
            )
        )

    def names(self) -> tuple[str, ...]:
        """
        Return aggregators that have both an instance
        and a request queue.
        """

        return tuple(
            name
            for name in self._instances.names()
            if self._queues.contains(name)
        )

    def get_instance(
        self,
        aggregator_name: str,
    ) -> AggregatorInterface:
        """Return a configured aggregator instance."""

        instance = self._instances.get(
            aggregator_name
        )

        if instance is None:
            raise KeyError(
                f"Unknown configured aggregator: "
                f"'{aggregator_name}'."
            )

        return instance
