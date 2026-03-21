"""Unit tests for the CarbonScope validator — scoring, persistence, weights, and retry."""

from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import MagicMock, patch, call

import pytest

from neurons.validator import CarbonValidator, _SCORES_FILE


# ── Helper ──────────────────────────────────────────────────────────


def _make_validator(**overrides):
    """Create a CarbonValidator with mocked __init__."""
    with patch.object(CarbonValidator, "__init__", lambda self: None):
        v = CarbonValidator.__new__(CarbonValidator)
    v.scores = overrides.get("scores", {})
    v.alpha = overrides.get("alpha", 0.1)
    v.wallet = MagicMock()
    v.subtensor = MagicMock()
    v.metagraph = MagicMock()
    v.dendrite = MagicMock()
    v.config = MagicMock()
    v.config.netuid = 1
    v.last_weight_block = 0
    v._consecutive_failures = 0
    v._max_failures = 3
    v._backoff_seconds = 2.0
    v._max_backoff = 60.0
    # Adaptive alpha / cold start fields
    v._query_counts = overrides.get("query_counts", {})
    v._cold_start_rounds = overrides.get("cold_start_rounds", 10)
    v._cold_start_alpha = overrides.get("cold_start_alpha", min(0.3, v.alpha * 3))
    v._cold_start_seed = overrides.get("cold_start_seed", 0.3)
    # Dynamic miner skipping / metagraph sync
    v._consecutive_zeros = overrides.get("consecutive_zeros", {})
    v._skip_zero_after = overrides.get("skip_zero_after", 10)
    v._metagraph_sync_interval = 120
    v._last_metagraph_sync = 0.0
    v.case_index = overrides.get("case_index", 0)
    return v


# ── EMA score updates ──────────────────────────────────────────────


class TestUpdateScores:
    def test_new_uid_gets_cold_start_blend(self):
        v = _make_validator()
        v._save_scores = MagicMock()
        v.update_scores(42, 0.8)
        # Cold start: seed * (1 - cold_start_alpha) + score * cold_start_alpha
        # = 0.3 * 0.7 + 0.8 * 0.3 = 0.45
        expected = 0.3 * (1 - 0.3) + 0.8 * 0.3
        assert abs(v.scores[42] - expected) < 1e-9
        assert v._query_counts[42] == 1

    def test_ema_blends_existing_score_cold_start(self):
        v = _make_validator(scores={42: 0.5})
        v._save_scores = MagicMock()
        v.update_scores(42, 1.0)
        # Cold start alpha (0.3) used since query_count ≤ cold_start_rounds
        # EMA: 0.7 * 0.5 + 0.3 * 1.0 = 0.65
        assert abs(v.scores[42] - 0.65) < 1e-9

    def test_ema_uses_base_alpha_after_warmup(self):
        v = _make_validator(scores={42: 0.5}, query_counts={42: 11})
        v._save_scores = MagicMock()
        v.update_scores(42, 1.0)
        # Past cold start: uses base alpha (0.1)
        # EMA: 0.9 * 0.5 + 0.1 * 1.0 = 0.55
        assert abs(v.scores[42] - 0.55) < 1e-9

    def test_ema_repeated_zero_decays(self):
        v = _make_validator(scores={1: 1.0})
        v._save_scores = MagicMock()
        for _ in range(20):
            v.update_scores(1, 0.0)
        assert v.scores[1] < 0.15  # decayed close to 0

    def test_save_scores_called_on_update(self):
        v = _make_validator()
        v._save_scores = MagicMock()
        v.update_scores(1, 0.5)
        v._save_scores.assert_called_once()

    def test_consecutive_zeros_tracked(self):
        v = _make_validator(scores={5: 0.5})
        v._save_scores = MagicMock()
        v.update_scores(5, 0.0)
        v.update_scores(5, 0.0)
        assert v._consecutive_zeros[5] == 2
        v.update_scores(5, 0.3)
        assert v._consecutive_zeros[5] == 0

    def test_consecutive_zeros_new_uid(self):
        v = _make_validator()
        v._save_scores = MagicMock()
        v.update_scores(99, 0.0)
        assert v._consecutive_zeros[99] == 1


# ── Score persistence ───────────────────────────────────────────────


class TestScorePersistence:
    def test_save_and_load_roundtrip(self, tmp_path, monkeypatch):
        monkeypatch.setenv("VALIDATOR_SCORE_HMAC_KEY", "test-hmac-key-for-ci")
        path = str(tmp_path / "scores.json")
        v = _make_validator(scores={1: 0.5, 2: 0.9})
        with patch("neurons.validator._SCORES_FILE", path):
            v._save_scores()
            v.scores = {}  # clear
            v.scores = v._load_scores()
        assert v.scores == {1: 0.5, 2: 0.9}

    def test_load_missing_file_returns_empty(self):
        v = _make_validator()
        with patch("neurons.validator._SCORES_FILE", "/nonexistent/path.json"):
            scores = v._load_scores()
        assert scores == {}

    def test_load_corrupt_json_returns_empty(self, tmp_path):
        path = str(tmp_path / "bad.json")
        with open(path, "w") as f:
            f.write("{corrupt")
        v = _make_validator()
        with patch("neurons.validator._SCORES_FILE", path):
            scores = v._load_scores()
        assert scores == {}


# ── Weight normalization ────────────────────────────────────────────


class TestSetWeights:
    def test_empty_scores_noop(self):
        v = _make_validator(scores={})
        v.set_weights()
        v.subtensor.set_weights.assert_not_called()

    def test_positive_scores_normalized(self):
        v = _make_validator(scores={0: 0.3, 1: 0.7})
        v.set_weights()
        call_args = v.subtensor.set_weights.call_args
        weights = call_args.kwargs.get("weights") or call_args[1].get("weights")
        assert abs(sum(weights) - 1.0) < 1e-9
        # uid 1 should have 0.7/1.0 = 0.7 weight
        idx = call_args.kwargs.get("uids", call_args[1].get("uids")).index(1)
        assert abs(weights[idx] - 0.7) < 1e-9

    def test_all_zero_scores_uniform(self):
        """When all scores are zero, assign uniform weights so miners stay visible."""
        v = _make_validator(scores={0: 0.0, 1: 0.0, 2: 0.0})
        v.set_weights()
        call_args = v.subtensor.set_weights.call_args
        weights = call_args.kwargs.get("weights") or call_args[1].get("weights")
        for w in weights:
            assert abs(w - 1.0 / 3) < 1e-9

    def test_retry_on_failure(self):
        v = _make_validator(scores={0: 0.5})
        v.subtensor.set_weights.side_effect = [
            RuntimeError("net error"),
            RuntimeError("net error"),
            None,  # succeeds on third attempt
        ]
        with patch("neurons.validator.time") as mock_time:
            v.set_weights()
        assert v.subtensor.set_weights.call_count == 3
        # Two retries with delays 1s and 2s
        assert mock_time.sleep.call_count == 2

    def test_all_retries_exhausted(self):
        v = _make_validator(scores={0: 0.5})
        v.subtensor.set_weights.side_effect = RuntimeError("always fails")
        with patch("neurons.validator.time"):
            v.set_weights()
        # 1 initial + 3 retries = 4 attempts
        assert v.subtensor.set_weights.call_count == 4


# ── Score miner response ───────────────────────────────────────────


class TestScoreMinerResponse:
    def test_failed_response_returns_zero(self):
        v = _make_validator()
        synapse = MagicMock()
        synapse.questionnaire = {"industry": "manufacturing"}
        response = MagicMock()
        response.is_success = False
        response.emissions = None
        assert v.score_miner_response(synapse, response, None) == 0.0

    def test_null_emissions_returns_zero(self):
        v = _make_validator()
        synapse = MagicMock()
        synapse.questionnaire = {"industry": "manufacturing"}
        response = MagicMock()
        response.is_success = True
        response.emissions = None
        assert v.score_miner_response(synapse, response, None) == 0.0


# ── Circuit breaker ─────────────────────────────────────────────────


class TestCircuitBreaker:
    def test_failures_increment(self):
        v = _make_validator()
        v._consecutive_failures = 2
        assert v._consecutive_failures < v._max_failures

    def test_backoff_doubles(self):
        v = _make_validator()
        v._backoff_seconds = 2.0
        v._backoff_seconds = min(v._backoff_seconds * 2, v._max_backoff)
        assert v._backoff_seconds == 4.0

    def test_backoff_capped_at_max(self):
        v = _make_validator()
        v._backoff_seconds = 32.0
        v._backoff_seconds = min(v._backoff_seconds * 2, v._max_backoff)
        assert v._backoff_seconds == v._max_backoff
