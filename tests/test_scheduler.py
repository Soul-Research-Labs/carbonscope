"""Tests for api.services.scheduler — start/stop, locking, and task management."""

from __future__ import annotations

import asyncio
from unittest.mock import patch, MagicMock

import pytest

from api.services import scheduler


@pytest.fixture(autouse=True)
def reset_scheduler_state():
    """Ensure no tasks leak between tests."""
    scheduler._scheduler_task = None
    scheduler._credit_reset_task = None
    scheduler._webhook_retry_task = None
    scheduler._token_cleanup_task = None
    scheduler._redis_client = None
    yield
    # Clean up any tasks created during the test
    for attr in ("_scheduler_task", "_credit_reset_task", "_webhook_retry_task", "_token_cleanup_task"):
        task = getattr(scheduler, attr, None)
        if task and not task.done():
            task.cancel()
    scheduler._scheduler_task = None
    scheduler._credit_reset_task = None
    scheduler._webhook_retry_task = None
    scheduler._token_cleanup_task = None
    scheduler._redis_client = None


# ── _acquire_lock tests ──────────────────────────────────────────────


def test_acquire_lock_no_redis_returns_true():
    """Without Redis, acquire_lock always returns True (single-instance mode)."""
    scheduler._redis_client = None
    with patch.dict("os.environ", {}, clear=True):
        # Force _redis_client to remain None
        scheduler._redis_client = None
        assert scheduler._acquire_lock("test_lock", 60) is True


def test_acquire_lock_redis_success():
    """When Redis is available and set returns True, lock is acquired."""
    mock_redis = MagicMock()
    mock_redis.set.return_value = True
    scheduler._redis_client = mock_redis
    assert scheduler._acquire_lock("test_lock", 60) is True
    mock_redis.set.assert_called_once_with("carbonscope:lock:test_lock", "1", nx=True, ex=60)


def test_acquire_lock_redis_failure():
    """When Redis set returns False, lock not acquired."""
    mock_redis = MagicMock()
    mock_redis.set.return_value = False
    scheduler._redis_client = mock_redis
    assert scheduler._acquire_lock("test_lock", 60) is False


def test_acquire_lock_redis_connection_error():
    """On OSError, acquire_lock returns True (fail-open)."""
    mock_redis = MagicMock()
    mock_redis.set.side_effect = OSError("Connection refused")
    scheduler._redis_client = mock_redis
    assert scheduler._acquire_lock("test_lock", 60) is True


# ── _get_redis tests ────────────────────────────────────────────────


def test_get_redis_no_url_returns_none():
    scheduler._redis_client = None
    with patch.dict("os.environ", {}, clear=True):
        result = scheduler._get_redis()
    assert result is None


def test_get_redis_returns_cached_client():
    mock_redis = MagicMock()
    scheduler._redis_client = mock_redis
    assert scheduler._get_redis() is mock_redis


# ── start/stop scheduler tests ──────────────────────────────────────


@pytest.mark.asyncio
async def test_start_scheduler_creates_tasks():
    """start_scheduler should create 4 asyncio tasks."""
    scheduler.start_scheduler()
    assert scheduler._scheduler_task is not None
    assert scheduler._credit_reset_task is not None
    assert scheduler._webhook_retry_task is not None
    assert scheduler._token_cleanup_task is not None
    # Clean up
    await scheduler.stop_scheduler()


@pytest.mark.asyncio
async def test_stop_scheduler_cancels_tasks():
    """stop_scheduler should set all globals back to None."""
    scheduler.start_scheduler()
    await scheduler.stop_scheduler()
    assert scheduler._scheduler_task is None
    assert scheduler._credit_reset_task is None
    assert scheduler._webhook_retry_task is None
    assert scheduler._token_cleanup_task is None


@pytest.mark.asyncio
async def test_start_scheduler_idempotent():
    """Calling start_scheduler twice should not create duplicate tasks."""
    scheduler.start_scheduler()
    task1 = scheduler._scheduler_task
    scheduler.start_scheduler()
    task2 = scheduler._scheduler_task
    assert task1 is task2
    await scheduler.stop_scheduler()


@pytest.mark.asyncio
async def test_stop_scheduler_noop_when_not_started():
    """stop_scheduler should not raise when no tasks exist."""
    await scheduler.stop_scheduler()  # Should not raise
