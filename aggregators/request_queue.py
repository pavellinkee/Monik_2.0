"""
Aggregator request queue.

Responsibility:
    Controls request priority for one aggregator.

Rules:
    - Stage 2 has higher priority than Stage 1.
    - Requests for the same aggregator are processed sequentially.
    - Rate limiting is handled by RateLimiter.
    - Different aggregators use different queues.
    - Requests already being processed cannot be preempted.
    - Among waiting requests, Stage 2 is always selected first.

Does NOT:
    - make HTTP requests;
    - calculate opportunities;
    - decide scanner logic;
    - send Telegram messages;
    - implement rate limiting itself.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from aggregators.rate_limiter import RateLimiter


STAGE_1_PRIORITY = 1
STAGE_2_PRIORITY = 0


@dataclass(order=True)
class _QueueItem:
    """Internal priority queue item."""

    priority: int
    sequence: int
    request: Callable[[], Awaitable[Any]] = field(
        compare=False
    )
    future: asyncio.Future[Any] = field(
        compare=False
    )


class AggregatorRequestQueue:
    """
    Priority queue for requests to one aggregator.

    One queue instance belongs to one aggregator.

    Example:

        1inch → AggregatorRequestQueue
        0x    → AggregatorRequestQueue
        Velora → AggregatorRequestQueue

    Each queue has its own RateLimiter.
    """

    def __init__(
        self,
        rate_limiter: RateLimiter,
    ):
        if not isinstance(
            rate_limiter,
            RateLimiter,
        ):
            raise TypeError(
                "rate_limiter must be a RateLimiter."
            )

        self._rate_limiter = rate_limiter

        self._queue: asyncio.PriorityQueue[
            _QueueItem
        ] = asyncio.PriorityQueue()

        self._sequence = 0

        self._worker_task: (
            asyncio.Task[None] | None
        ) = None

        self._stopping = False

    @property
    def is_running(self) -> bool:
        """Return whether the queue worker is running."""

        return (
            self._worker_task is not None
            and not self._worker_task.done()
        )

    @property
    def pending_count(self) -> int:
        """Return the number of requests waiting in the queue."""

        return self._queue.qsize()

    async def start(self) -> None:
        """
        Start the queue worker.

        Calling start() multiple times is safe.
        """

        if self.is_running:
            return

        self._stopping = False

        self._worker_task = asyncio.create_task(
            self._worker()
        )

    async def stop(self) -> None:
        """
        Stop the queue worker.

        Pending requests that have not started are cancelled.
        A request currently being executed is cancelled together
        with the worker task.
        """

        if self._worker_task is None:
            self._cancel_pending_requests()

            self._stopping = True

            return

        self._stopping = True

        self._cancel_pending_requests()

        worker_task = self._worker_task

        worker_task.cancel()

        try:
            await worker_task

        except asyncio.CancelledError:
            pass

        finally:
            self._worker_task = None

    async def submit(
        self,
        request: Callable[[], Awaitable[Any]],
        stage: int,
    ) -> Any:
        """
        Add a request to the queue and wait for its result.

        Stage 2 has higher priority than Stage 1.

        Requests with the same priority are processed in
        FIFO order.

        The request itself is an async callable with no arguments.
        """

        if not callable(request):
            raise TypeError(
                "request must be callable."
            )

        priority = self._get_priority(stage)

        if self._stopping:
            raise RuntimeError(
                "Cannot submit request: "
                "queue is stopping."
            )

        if not self.is_running:
            await self.start()

        loop = asyncio.get_running_loop()

        future: asyncio.Future[Any] = (
            loop.create_future()
        )

        item = _QueueItem(
            priority=priority,
            sequence=self._sequence,
            request=request,
            future=future,
        )

        self._sequence += 1

        await self._queue.put(item)

        return await future

    async def wait_until_empty(self) -> None:
        """
        Wait until all currently queued requests are processed.
        """

        await self._queue.join()

    async def _worker(self) -> None:
        """Process queued requests sequentially."""

        while True:
            item = await self._queue.get()

            try:
                if item.future.cancelled():
                    continue

                await self._rate_limiter.wait()

                if item.future.cancelled():
                    continue

                result = await item.request()

                if not item.future.done():
                    item.future.set_result(
                        result
                    )

            except asyncio.CancelledError:
                if not item.future.done():
                    item.future.cancel()

                raise

            except Exception as error:
                if not item.future.done():
                    item.future.set_exception(
                        error
                    )

            finally:
                self._queue.task_done()

    @staticmethod
    def _get_priority(
        stage: int,
    ) -> int:
        """Convert scanner stage to queue priority."""

        if stage == 2:
            return STAGE_2_PRIORITY

        if stage == 1:
            return STAGE_1_PRIORITY

        raise ValueError(
            "stage must be 1 or 2"
        )

    def _cancel_pending_requests(self) -> None:
        """
        Cancel all requests that are still waiting in the queue.

        The currently executing request is handled by cancellation
        of the worker task.
        """

        while True:
            try:
                item = self._queue.get_nowait()

            except asyncio.QueueEmpty:
                break

            try:
                if not item.future.done():
                    item.future.cancel()

            finally:
                self._queue.task_done()
