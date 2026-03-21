"""Unit tests for the CarbonScope miner — input validation, blacklisting, and error handling."""

from __future__ import annotations

from collections import OrderedDict, deque
from unittest.mock import MagicMock, patch
import pytest
from pydantic import ValidationError

from neurons.miner import (
    CarbonMiner,
    ProvidedDataInput,
    QuestionnaireInput,
    VALID_INDUSTRIES,
    VALID_FUEL_TYPES,
)


# ── Input validation schemas ────────────────────────────────────────


class TestProvidedDataInput:
    def test_defaults(self):
        data = ProvidedDataInput()
        assert data.fuel_use_liters == 0
        assert data.fuel_type == "diesel"

    def test_valid_data(self):
        data = ProvidedDataInput(
            fuel_use_liters=5000,
            electricity_kwh=100000,
            employee_count=50,
        )
        assert data.fuel_use_liters == 5000
        assert data.electricity_kwh == 100000

    def test_negative_fuel_rejected(self):
        with pytest.raises(ValidationError):
            ProvidedDataInput(fuel_use_liters=-100)

    def test_exceeding_bounds_rejected(self):
        with pytest.raises(ValidationError):
            ProvidedDataInput(fuel_use_liters=999_999_999)

    def test_invalid_fuel_type_rejected(self):
        with pytest.raises(ValidationError):
            ProvidedDataInput(fuel_type="plutonium")

    def test_valid_fuel_types(self):
        for ft in VALID_FUEL_TYPES:
            data = ProvidedDataInput(fuel_type=ft)
            assert data.fuel_type == ft

    def test_extra_fields_allowed(self):
        data = ProvidedDataInput(custom_field="test")
        assert data.model_dump()["custom_field"] == "test"


class TestQuestionnaireInput:
    def test_defaults(self):
        q = QuestionnaireInput()
        assert q.industry == "manufacturing"
        assert q.region == "US"
        assert q.year == 2025

    def test_valid_industries(self):
        for ind in VALID_INDUSTRIES:
            q = QuestionnaireInput(industry=ind)
            assert q.industry == ind

    def test_invalid_industry_rejected(self):
        with pytest.raises(ValidationError):
            QuestionnaireInput(industry="space_mining")

    def test_year_bounds(self):
        with pytest.raises(ValidationError):
            QuestionnaireInput(year=1800)
        with pytest.raises(ValidationError):
            QuestionnaireInput(year=2200)

    def test_case_insensitive_industry(self):
        q = QuestionnaireInput(industry="MANUFACTURING")
        assert q.industry == "manufacturing"


# ── Blacklist logic ─────────────────────────────────────────────────


def _make_miner(**overrides):
    """Create a CarbonMiner with mocked __init__ and sensible defaults."""
    with patch.object(CarbonMiner, "__init__", lambda self: None):
        m = CarbonMiner.__new__(CarbonMiner)
    m.metagraph = MagicMock()
    m.metagraph.hotkeys = ["hk_validator_1", "hk_miner_1"]
    m.metagraph.validator_permit = [True, False]
    m._request_times = OrderedDict()
    m._RATE_LIMIT_MAX = overrides.get("rate_limit_max", 3)
    m._RATE_LIMIT_WINDOW = overrides.get("rate_limit_window", 60)
    return m


class TestBlacklist:
    @pytest.fixture
    def miner(self):
        return _make_miner()

    def test_unregistered_hotkey_blocked(self, miner):
        synapse = MagicMock()
        synapse.dendrite.hotkey = "unknown_hotkey"
        blocked, reason = miner.blacklist(synapse)
        assert blocked is True
        assert "Unregistered" in reason

    def test_non_validator_blocked(self, miner):
        synapse = MagicMock()
        synapse.dendrite.hotkey = "hk_miner_1"  # not a validator
        blocked, reason = miner.blacklist(synapse)
        assert blocked is True
        assert "not a validator" in reason

    def test_valid_validator_allowed(self, miner):
        synapse = MagicMock()
        synapse.dendrite.hotkey = "hk_validator_1"
        blocked, _ = miner.blacklist(synapse)
        assert blocked is False

    def test_rate_limiting(self, miner):
        synapse = MagicMock()
        synapse.dendrite.hotkey = "hk_validator_1"

        # First 3 requests succeed (rate limit max = 3)
        for _ in range(3):
            blocked, _ = miner.blacklist(synapse)
            assert blocked is False

        # 4th request is rate-limited
        blocked, reason = miner.blacklist(synapse)
        assert blocked is True
        assert "Rate limited" in reason

    def test_rate_limit_window_expires(self, miner):
        """After the window passes old entries are evicted."""
        import time as _time

        synapse = MagicMock()
        synapse.dendrite.hotkey = "hk_validator_1"

        # Fill up the rate limit
        for _ in range(3):
            miner.blacklist(synapse)

        # Manually expire all timestamps
        for d in miner._request_times.values():
            for i in range(len(d)):
                d[i] = d[i] - miner._RATE_LIMIT_WINDOW - 1

        blocked, _ = miner.blacklist(synapse)
        assert blocked is False


# ── Forward / error handling ────────────────────────────────────────


class TestForward:
    @pytest.fixture
    def miner(self):
        return _make_miner()

    def test_validation_error_returns_neg1(self, miner):
        synapse = MagicMock()
        synapse.questionnaire = {"industry": "invalid_industry_xyz"}
        synapse.context = {}

        result = miner.forward(synapse)
        assert result.confidence == -1.0
        assert "Validation error" in result.assumptions[0]

    def test_internal_error_returns_neg2(self, miner):
        """If _estimate raises an unexpected exception → confidence -2.0."""
        synapse = MagicMock()
        synapse.questionnaire = {"industry": "manufacturing"}
        synapse.context = {}

        with patch.object(miner, "_estimate", side_effect=RuntimeError("boom")):
            result = miner.forward(synapse)
        assert result.confidence == -2.0
        assert "internal error" in result.assumptions[0]

    def test_successful_estimation(self, miner):
        synapse = MagicMock()
        synapse.questionnaire = {
            "company": "TestCorp",
            "industry": "manufacturing",
            "provided_data": {"electricity_kwh": 50000},
            "region": "US",
            "year": 2025,
        }
        synapse.context = {}

        result = miner.forward(synapse)
        assert result.emissions is not None
        assert result.emissions["total"] >= 0
        assert 0 <= result.confidence <= 1
