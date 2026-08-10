"""
Aggregator request queue.

Responsibility:
    Controls request priority for one aggregator.

Rules:
    - Stage 2 has higher priority than Stage 1.
    - Requests for the same aggregator are processed sequentially.
    - Rate limiting is handled by RateLimiter.
    - Different aggregators use different queues.

Does NOT:
    - make HTTP requests;
    - calculate opportunities;
    - decide scanner logic;
    - send Telegram messages.
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
    """Priority queue for requests to one aggregator."""

    def __init__(
        self,
        rate_limiter: RateLimiter,
    ):
        if not isinstance(
            rate_limiter,
            RateLimiter,
        ):
            raise TypeError(
                "rate_limiter must be a RateLimiter"
            )

        self._rate_limiter = rate_limiter

        self._queue: asyncio.PriorityQueue[
            _QueueItem
        ] = asyncio.PriorityQueue()

        self._sequence = 0
        self._worker_task: asyncio.Task[
            None
        ] | None = None

        self._stopping = False

    @property
    def is_running(self) -> bool:
        """Return whether the worker is running."""

        return (
            self._worker_task is not None
            and not self._worker_task.done()
        )

    @property
    def pending_count(self) -> int:
        """Return the number of queued requests."""

        return self._queue.qsize()

    async def start(self) -> None:
        """Start the queue worker."""

        if self.is_running:
            return

        self._stopping = False

        self._worker_task = asyncio.create_task(
            self._worker()
        )

    async def stop(self) -> None:
        """
        Stop the queue worker.

        All pending requests are cancelled.
        The queue can be started again afterwards.
        """

        worker = self._worker_task

        if worker is None:
            self._cancel_pending_requests()
            self._stopping = False
            return

        self._stopping = True

        worker.cancel()

        try:
            await worker
        except asyncio.CancelledError:
            pass

        self._cancel_pending_requests()

        self._worker_task = None
        self._stopping = False

    async def submit(
        self,
        request: Callable[[], Awaitable[Any]],
        stage: int,
    ) -> Any:
        """
        Add a request to the queue.

        Stage 2 receives higher priority than Stage 1.
        """

        if not callable(request):
            raise TypeError(
                "request must be callable"
            )

        if stage == 2:
            priority = STAGE_2_PRIORITY

        elif stage == 1:
            priority = STAGE_1_PRIORITY

        else:
            raise ValueError(
                "stage must be 1 or 2"
            )

        if not self.is_running:
            await self.start()

        if self._stopping:
            raise RuntimeError(
                "Cannot submit request: "
                "queue is stopping."
            )

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
        Wait until all currently queued requests
        have been processed.
        """

        await self._queue.join()

    async def _worker(self) -> None:
        """Process queued requests sequentially."""

        try:
            while True:
                item = await self._queue.get()

                try:
                    await self._rate_limiter.wait()

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

        except asyncio.CancelledError:
            raise

    def _cancel_pending_requests(self) -> None:
        """
        Cancel all requests still waiting in the queue.
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
