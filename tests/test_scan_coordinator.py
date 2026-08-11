import asyncio

import pytest

from core.scan_coordinator import (
    ScanCoordinator,
)


@pytest.mark.asyncio
async def test_stage1_runner_is_executed():
    calls = []

    async def stage1():
        calls.append("stage1")

    async def stage2():
        calls.append("stage2")

    coordinator = ScanCoordinator(
        stage1_runner=stage1,
        stage2_runner=stage2,
        stage1_interval_seconds=0.001,
    )

    await coordinator.run_stage1()

    assert calls == ["stage1"]


@pytest.mark.asyncio
async def test_stage2_priority():
    calls = []

    async def stage1():
        calls.append("stage1")

    async def stage2():
        calls.append("stage2")

    coordinator = ScanCoordinator(
        stage1_runner=stage1,
        stage2_runner=stage2,
        stage1_interval_seconds=0.001,
        stage2_priority=True,
    )

    await coordinator.run_cycle()

    assert calls == [
        "stage2",
        "stage1",
    ]


@pytest.mark.asyncio
async def test_stage1_priority_can_be_disabled():
    calls = []

    async def stage1():
        calls.append("stage1")

    async def stage2():
        calls.append("stage2")

    coordinator = ScanCoordinator(
        stage1_runner=stage1,
        stage2_runner=stage2,
        stage1_interval_seconds=0.001,
        stage2_priority=False,
    )

    await coordinator.run_cycle()

    assert calls == [
        "stage1",
        "stage2",
    ]


@pytest.mark.asyncio
async def test_stage2_concurrency_is_limited():
    active = 0
    maximum = 0

    async def stage1():
        return None

    async def stage2():
        nonlocal active
        nonlocal maximum

        active += 1
        maximum = max(
            maximum,
            active,
        )

        await asyncio.sleep(0.01)

        active -= 1

    coordinator = ScanCoordinator(
        stage1_runner=stage1,
        stage2_runner=stage2,
        stage1_interval_seconds=0.001,
        stage2_max_concurrent_checks=2,
    )

    tasks = [
        await coordinator.submit_stage2()
        for _ in range(5)
    ]

    await asyncio.gather(*tasks)

    assert maximum <= 2


@pytest.mark.asyncio
async def test_run_stage2_returns_runner_result():
    async def stage1():
        return None

    async def stage2():
        return "stage2-result"

    coordinator = ScanCoordinator(
        stage1_runner=stage1,
        stage2_runner=stage2,
    )

    result = await coordinator.run_stage2()

    assert result == "stage2-result"


@pytest.mark.asyncio
async def test_run_alias_is_compatible():
    called = False

    async def stage1():
        nonlocal called
        called = True

    async def stage2():
        return None

    coordinator = ScanCoordinator(
        stage1_runner=stage1,
        stage2_runner=stage2,
        stage1_interval_seconds=0.001,
    )

    task = asyncio.create_task(
        coordinator.run()
    )

    await asyncio.sleep(0.01)

    coordinator.stop()

    await asyncio.wait_for(
        task,
        timeout=1,
    )

    assert called is True


def test_invalid_stage1_runner_is_rejected():
    with pytest.raises(TypeError):
        ScanCoordinator(
            stage1_runner=None,
            stage2_runner=lambda: None,
        )


def test_invalid_stage2_runner_is_rejected():
    with pytest.raises(TypeError):
        ScanCoordinator(
            stage1_runner=lambda: None,
            stage2_runner=None,
        )


def test_invalid_stage1_interval_is_rejected():
    with pytest.raises(ValueError):
        ScanCoordinator(
            stage1_runner=lambda: None,
            stage2_runner=lambda: None,
            stage1_interval_seconds=0,
        )


def test_invalid_stage2_concurrency_is_rejected():
    with pytest.raises(ValueError):
        ScanCoordinator(
            stage1_runner=lambda: None,
            stage2_runner=lambda: None,
            stage2_max_concurrent_checks=0,
        )
