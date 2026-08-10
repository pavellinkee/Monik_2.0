"""
Tests for AggregatorRequestQueue.
"""

import asyncio

import pytest

from aggregators.rate_limiter import (
    RateLimiter,
)
from aggregators.request_queue import (
    AggregatorRequestQueue,
    STAGE_1_PRIORITY,
    STAGE_2_PRIORITY,
)


def create_queue(
    interval: float = 0.0,
) -> AggregatorRequestQueue:
    """Create a test queue."""

    limiter = RateLimiter(
        standard_interval=interval,
        max_interval=10.0,
    )

    return AggregatorRequestQueue(
        rate_limiter=limiter
    )


@pytest.mark.asyncio
async def test_first_request_is_processed():
    """A submitted request returns its result."""

    queue = create_queue()

    result = await queue.submit(
        lambda: asyncio.sleep(
            0,
            result="success",
        ),
        stage=1,
    )

    assert result == "success"

    await queue.stop()


@pytest.mark.asyncio
async def test_stage_2_has_higher_priority():
    """
    Stage 2 is processed before waiting Stage 1 requests.
    """

    queue = create_queue()

    await queue.start()

    processed: list[str] = []

    first_started = asyncio.Event()
    release_first = asyncio.Event()

    async def first_stage_1():
        processed.append("stage1-running")

        first_started.set()

        await release_first.wait()

        processed.append("stage1-finished")

        return "stage1"

    async def second_stage_1():
        processed.append("stage1-second")

        return "stage1-second"

    async def stage_2():
        processed.append("stage2")

        return "stage2"

    first_task = asyncio.create_task(
        queue.submit(
            first_stage_1,
            stage=1,
        )
    )

    await first_started.wait()

    second_task = asyncio.create_task(
        queue.submit(
            second_stage_1,
            stage=1,
        )
    )

    stage_2_task = asyncio.create_task(
        queue.submit(
            stage_2,
            stage=2,
        )
    )

    await asyncio.sleep(0)

    release_first.set()

    await asyncio.gather(
        first_task,
        second_task,
        stage_2_task,
    )

    await queue.stop()

    assert processed == [
        "stage1-running",
        "stage1-finished",
        "stage2",
        "stage1-second",
    ]


@pytest.mark.asyncio
async def test_same_priority_uses_fifo_order():
    """Requests with equal priority preserve insertion order."""

    queue = create_queue()

    results: list[str] = []

    async def make_request(
        name: str,
    ):
        results.append(name)

        return name

    tasks = [
        asyncio.create_task(
            queue.submit(
                lambda name=name: make_request(name),
                stage=2,
            )
        )
        for name in (
            "first",
            "second",
            "third",
        )
    ]

    returned = await asyncio.gather(
        *tasks
    )

    await queue.stop()

    assert results == [
        "first",
        "second",
        "third",
    ]

    assert returned == [
        "first",
        "second",
        "third",
    ]


@pytest.mark.asyncio
async def test_requests_are_processed_sequentially():
    """
    Two requests for the same aggregator never execute
    simultaneously.
    """

    queue = create_queue()

    active = 0
    maximum_active = 0

    async def request():
        nonlocal active
        nonlocal maximum_active

        active += 1

        maximum_active = max(
            maximum_active,
            active,
        )

        await asyncio.sleep(0.01)

        active -= 1

        return "done"

    results = await asyncio.gather(
        queue.submit(
            request,
            stage=1,
        ),
        queue.submit(
            request,
            stage=1,
        ),
        queue.submit(
            request,
            stage=1,
        ),
    )

    await queue.stop()

    assert results == [
        "done",
        "done",
        "done",
    ]

    assert maximum_active == 1


@pytest.mark.asyncio
async def test_rate_limiter_is_called_before_request():
    """
    The queue uses the configured RateLimiter before
    executing the request.
    """

    queue = create_queue()

    called = False

    original_wait = (
        queue._rate_limiter.wait
    )

    async def tracked_wait():
        nonlocal called

        called = True

        await original_wait()

    queue._rate_limiter.wait = tracked_wait

    result = await queue.submit(
        lambda: asyncio.sleep(
            0,
            result="ok",
        ),
        stage=1,
    )

    await queue.stop()

    assert result == "ok"
    assert called is True


@pytest.mark.asyncio
async def test_request_exception_is_returned_to_caller():
    """Exceptions from requests reach the caller."""

    queue = create_queue()

    async def failing_request():
        raise RuntimeError(
            "test error"
        )

    with pytest.raises(RuntimeError):
        await queue.submit(
            failing_request,
            stage=1,
        )

    await queue.stop()


@pytest.mark.asyncio
async def test_invalid_stage_is_rejected():
    """Only Stage 1 and Stage 2 are allowed."""

    queue = create_queue()

    with pytest.raises(ValueError):
        await queue.submit(
            lambda: asyncio.sleep(0),
            stage=3,
        )

    await queue.stop()


@pytest.mark.asyncio
async def test_non_callable_request_is_rejected():
    """Request must be callable."""

    queue = create_queue()

    with pytest.raises(TypeError):
        await queue.submit(
            "not callable",
            stage=1,
        )

    await queue.stop()


@pytest.mark.asyncio
async def test_pending_count_is_updated():
    """Pending queue count reflects waiting requests."""

    queue = create_queue(
        interval=0.05
    )

    started = asyncio.Event()
    release = asyncio.Event()

    async def long_request():
        started.set()

        await release.wait()

        return "done"

    first = asyncio.create_task(
        queue.submit(
            long_request,
            stage=1,
        )
    )

    await started.wait()

    second = asyncio.create_task(
        queue.submit(
            lambda: asyncio.sleep(
                0,
                result="second",
            ),
            stage=1,
        )
    )

    await asyncio.sleep(0)

    assert queue.pending_count >= 1

    release.set()

    await asyncio.gather(
        first,
        second,
    )

    await queue.stop()


@pytest.mark.asyncio
async def test_wait_until_empty_waits_for_all_requests():
    """wait_until_empty waits for all queued work."""

    queue = create_queue()

    processed: list[str] = []

    async def request(name: str):
        processed.append(name)

        await asyncio.sleep(0)

        return name

    tasks = [
        asyncio.create_task(
            queue.submit(
                lambda name=name: request(name),
                stage=1,
            )
        )
        for name in (
            "one",
            "two",
            "three",
        )
    ]

    await queue.wait_until_empty()

    assert processed == [
        "one",
        "two",
        "three",
    ]

    await asyncio.gather(
        *tasks
    )

    await queue.stop()


@pytest.mark.asyncio
async def test_stop_cancels_pending_requests():
    """Stopping a queue cancels pending requests."""

    queue = create_queue(
        interval=0.1
    )

    first_started = asyncio.Event()
    release_first = asyncio.Event()

    async def first_request():
        first_started.set()

        await release_first.wait()

        return "first"

    async def second_request():
        return "second"

    first_task = asyncio.create_task(
        queue.submit(
            first_request,
            stage=1,
        )
    )

    await first_started.wait()

    second_task = asyncio.create_task(
        queue.submit(
            second_request,
            stage=1,
        )
    )

    await asyncio.sleep(0)

    await queue.stop()

    release_first.set()

    with pytest.raises(
        asyncio.CancelledError
    ):
        await first_task

    with pytest.raises(
        asyncio.CancelledError
    ):
        await second_task


@pytest.mark.asyncio
async def test_queue_can_restart_after_stop():
    """A stopped queue can be started again."""

    queue = create_queue()

    result_1 = await queue.submit(
        lambda: asyncio.sleep(
            0,
            result=1,
        ),
        stage=1,
    )

    await queue.stop()

    result_2 = await queue.submit(
        lambda: asyncio.sleep(
            0,
            result=2,
        ),
        stage=1,
    )

    await queue.stop()

    assert result_1 == 1
    assert result_2 == 2


def test_stage_priority_constants():
    """Stage 2 priority is numerically higher than Stage 1."""

    assert STAGE_2_PRIORITY < STAGE_1_PRIORITY
