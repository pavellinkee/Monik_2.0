"""
Tests for AggregatorRequestQueue.

Covers:
    - sequential request processing;
    - Stage 2 priority;
    - Stage 1 FIFO ordering;
    - exceptions;
    - wait_until_empty();
    - queue restart after stop;
    - request serialization;
    - concurrent submissions.
"""

import asyncio

import pytest

from aggregators.rate_limiter import RateLimiter
from aggregators.request_queue import (
    AggregatorRequestQueue,
)


def create_queue() -> AggregatorRequestQueue:
    """Create a fast queue for tests."""

    limiter = RateLimiter(
        standard_interval=0.0,
        max_interval=1.0,
    )

    return AggregatorRequestQueue(
        rate_limiter=limiter,
    )


@pytest.mark.asyncio
async def test_queue_processes_requests_sequentially():
    """Requests for one aggregator are processed sequentially."""

    queue = create_queue()

    active = 0
    maximum_active = 0
    processed: list[str] = []

    async def request(name: str):
        nonlocal active
        nonlocal maximum_active

        active += 1
        maximum_active = max(
            maximum_active,
            active,
        )

        processed.append(
            f"{name}-start"
        )

        await asyncio.sleep(0.01)

        processed.append(
            f"{name}-finish"
        )

        active -= 1

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

    results = await asyncio.gather(
        *tasks
    )

    await queue.stop()

    assert results == [
        "one",
        "two",
        "three",
    ]

    assert maximum_active == 1

    assert processed == [
        "one-start",
        "one-finish",
        "two-start",
        "two-finish",
        "three-start",
        "three-finish",
    ]


@pytest.mark.asyncio
async def test_stage2_has_priority_over_waiting_stage1():
    """Stage 2 is processed before waiting Stage 1 requests."""

    queue = create_queue()

    processed: list[str] = []

    first_started = asyncio.Event()
    release_first = asyncio.Event()

    async def first_stage1():
        processed.append("first-stage1")

        first_started.set()

        await release_first.wait()

        return "first"

    async def second_stage1():
        processed.append("second-stage1")

        return "second"

    async def stage2():
        processed.append("stage2")

        return "stage2"

    first_task = asyncio.create_task(
        queue.submit(
            first_stage1,
            stage=1,
        )
    )

    await first_started.wait()

    second_task = asyncio.create_task(
        queue.submit(
            second_stage1,
            stage=1,
        )
    )

    stage2_task = asyncio.create_task(
        queue.submit(
            stage2,
            stage=2,
        )
    )

    await asyncio.sleep(0)

    release_first.set()

    results = await asyncio.gather(
        first_task,
        second_task,
        stage2_task,
    )

    await queue.stop()

    assert results == [
        "first",
        "second",
        "stage2",
    ]

    assert processed == [
        "first-stage1",
        "stage2",
        "second-stage1",
    ]


@pytest.mark.asyncio
async def test_stage1_requests_keep_fifo_order():
    """Stage 1 requests with equal priority keep FIFO order."""

    queue = create_queue()

    processed: list[str] = []

    async def request(name: str):
        processed.append(name)
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

    results = await asyncio.gather(
        *tasks
    )

    await queue.stop()

    assert results == [
        "one",
        "two",
        "three",
    ]

    assert processed == [
        "one",
        "two",
        "three",
    ]


@pytest.mark.asyncio
async def test_wait_until_empty_waits_for_all_requests():
    """wait_until_empty waits until queued work is complete."""

    queue = create_queue()

    processed: list[str] = []

    async def request(name: str):
        await asyncio.sleep(0.02)

        processed.append(name)

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

    # Give submit() tasks one event-loop turn so they
    # can actually enter the queue before join().
    await asyncio.sleep(0)

    await queue.wait_until_empty()

    results = await asyncio.gather(
        *tasks
    )

    await queue.stop()

    assert processed == [
        "one",
        "two",
        "three",
    ]

    assert results == [
        "one",
        "two",
        "three",
    ]


@pytest.mark.asyncio
async def test_request_exception_is_returned_to_submitter():
    """Request exceptions propagate to the submitter."""

    queue = create_queue()

    async def failing_request():
        raise RuntimeError(
            "test request failed"
        )

    with pytest.raises(
        RuntimeError,
        match="test request failed",
    ):
        await queue.submit(
            failing_request,
            stage=1,
        )

    await queue.stop()


@pytest.mark.asyncio
async def test_invalid_stage_is_rejected():
    """Only Stage 1 and Stage 2 are allowed."""

    queue = create_queue()

    async def request():
        return "ok"

    with pytest.raises(
        ValueError,
        match="stage must be 1 or 2",
    ):
        await queue.submit(
            request,
            stage=3,
        )

    await queue.stop()


@pytest.mark.asyncio
async def test_queue_can_restart_after_stop():
    """A queue can be stopped and started again."""

    queue = create_queue()

    async def first_request():
        return "first"

    async def second_request():
        return "second"

    first_result = await queue.submit(
        first_request,
        stage=1,
    )

    assert first_result == "first"

    await queue.stop()

    assert not queue.is_running

    second_result = await queue.submit(
        second_request,
        stage=1,
    )

    assert second_result == "second"

    await queue.stop()


@pytest.mark.asyncio
async def test_queue_reports_running_state():
    """Queue running state changes correctly."""

    queue = create_queue()

    assert not queue.is_running

    await queue.start()

    assert queue.is_running

    await queue.stop()

    assert not queue.is_running


@pytest.mark.asyncio
async def test_multiple_submissions_can_run_concurrently_at_submitter_level():
    """
    Multiple callers can submit requests concurrently,
    while the queue itself still processes them sequentially.
    """

    queue = create_queue()

    processed: list[str] = []

    async def request(name: str):
        await asyncio.sleep(0.005)

        processed.append(name)

        return name

    async def submit_request(name: str):
        return await queue.submit(
            lambda: request(name),
            stage=1,
        )

    results = await asyncio.gather(
        submit_request("one"),
        submit_request("two"),
        submit_request("three"),
        submit_request("four"),
    )

    await queue.stop()

    assert results == [
        "one",
        "two",
        "three",
        "four",
    ]

    assert processed == [
        "one",
        "two",
        "three",
        "four",
    ]
