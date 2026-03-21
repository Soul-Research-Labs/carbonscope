"""Tests for api.services.subnet_bridge — circuit breaker and local estimation."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from api.services import subnet_bridge


# ── Circuit breaker tests ────────────────────────────────────────────


@pytest.fixture(autouse=True)
def reset_circuit_breaker():
    """Reset circuit-breaker state before each test."""
    subnet_bridge._global_cb_failures = 0
    subnet_bridge._global_cb_opened_at = 0.0
    subnet_bridge._miner_cb.clear()
    yield
    subnet_bridge._global_cb_failures = 0
    subnet_bridge._global_cb_opened_at = 0.0
    subnet_bridge._miner_cb.clear()


def test_cb_initially_closed():
    assert not subnet_bridge._global_cb_is_open()


def test_cb_opens_after_threshold_failures():
    for _ in range(subnet_bridge._GLOBAL_CB_FAILURE_THRESHOLD):
        subnet_bridge._global_cb_record_failure()
    assert subnet_bridge._global_cb_is_open()


def test_cb_success_resets():
    for _ in range(subnet_bridge._GLOBAL_CB_FAILURE_THRESHOLD):
        subnet_bridge._global_cb_record_failure()
    assert subnet_bridge._global_cb_is_open()
    subnet_bridge._global_cb_record_success()
    assert not subnet_bridge._global_cb_is_open()


def test_cb_recovers_after_timeout():
    for _ in range(subnet_bridge._GLOBAL_CB_FAILURE_THRESHOLD):
        subnet_bridge._global_cb_record_failure()
    # Simulate passage of recovery timeout
    subnet_bridge._global_cb_opened_at = time.monotonic() - subnet_bridge._GLOBAL_CB_RECOVERY_TIMEOUT - 1
    assert not subnet_bridge._global_cb_is_open(), "Should be half-open after recovery timeout"


def test_cb_below_threshold_stays_closed():
    for _ in range(subnet_bridge._GLOBAL_CB_FAILURE_THRESHOLD - 1):
        subnet_bridge._global_cb_record_failure()
    assert not subnet_bridge._global_cb_is_open()


# ── Per-miner circuit breaker tests ────────────────────────────────


def test_per_miner_cb_initially_closed():
    assert not subnet_bridge._miner_cb_is_open(0)


def test_per_miner_cb_opens_after_failures():
    for _ in range(subnet_bridge._PER_MINER_FAILURE_THRESHOLD):
        subnet_bridge._miner_cb_record_failure(42)
    assert subnet_bridge._miner_cb_is_open(42)
    assert not subnet_bridge._miner_cb_is_open(99)  # other miners unaffected


def test_per_miner_cb_success_resets():
    for _ in range(subnet_bridge._PER_MINER_FAILURE_THRESHOLD):
        subnet_bridge._miner_cb_record_failure(42)
    assert subnet_bridge._miner_cb_is_open(42)
    subnet_bridge._miner_cb_record_success(42)
    assert not subnet_bridge._miner_cb_is_open(42)


# ── estimate_emissions — circuit breaker integration ────────────────


@pytest.mark.asyncio
async def test_estimate_emissions_raises_when_cb_open():
    for _ in range(subnet_bridge._GLOBAL_CB_FAILURE_THRESHOLD):
        subnet_bridge._global_cb_record_failure()
    with pytest.raises(RuntimeError, match="Circuit breaker open"):
        await subnet_bridge.estimate_emissions({"industry": "tech"})


# ── estimate_emissions_local tests ──────────────────────────────────


def test_local_estimation_default_questionnaire():
    result = subnet_bridge.estimate_emissions_local({"industry": "manufacturing"})
    assert "emissions" in result
    em = result["emissions"]
    assert "scope1" in em
    assert "scope2" in em
    assert "scope3" in em
    assert "total" in em
    assert em["total"] >= 0
    assert result["methodology_version"] == "ghg_protocol_v2025"


def test_local_estimation_with_fuel_data():
    q = {
        "industry": "manufacturing",
        "provided_data": {
            "fuel_use_liters": 1000,
            "fuel_type": "diesel",
            "electricity_kwh": 50000,
        },
    }
    result = subnet_bridge.estimate_emissions_local(q)
    em = result["emissions"]
    assert em["scope1"] > 0, "Fuel data should produce positive Scope 1"
    assert em["scope2"] > 0, "Electricity data should produce positive Scope 2"
    assert em["total"] > 0


def test_local_estimation_with_supplier_spend():
    q = {
        "industry": "technology",
        "provided_data": {"supplier_spend_usd": 100000},
    }
    result = subnet_bridge.estimate_emissions_local(q)
    # Scope 3 cat1 should be positive
    s3_detail = result["breakdown"]["scope3_detail"]
    assert "cat1_purchased_goods" in s3_detail
    assert s3_detail["cat1_purchased_goods"] > 0


def test_local_estimation_confidence():
    q = {
        "industry": "manufacturing",
        "provided_data": {
            "fuel_use_liters": 500,
            "electricity_kwh": 10000,
            "employee_count": 100,
        },
    }
    result = subnet_bridge.estimate_emissions_local(q)
    assert 0 <= result["confidence"] <= 1


def test_local_estimation_assumptions_empty_data():
    result = subnet_bridge.estimate_emissions_local({"industry": "manufacturing"})
    assert isinstance(result["assumptions"], list)
    assert len(result["assumptions"]) > 0, "Missing data should generate assumptions"


def test_local_estimation_sources():
    result = subnet_bridge.estimate_emissions_local({"industry": "manufacturing"})
    assert isinstance(result["sources"], list)
    assert len(result["sources"]) > 0


def test_local_estimation_region_override():
    q = {
        "industry": "manufacturing",
        "region": "EU",
        "provided_data": {"electricity_kwh": 10000},
    }
    result = subnet_bridge.estimate_emissions_local(q)
    assert result["emissions"]["scope2"] > 0


def test_local_estimation_refrigerant():
    q = {
        "industry": "manufacturing",
        "provided_data": {
            "refrigerant_type": "R-410A",
            "refrigerant_kg_leaked": 5,
        },
    }
    result = subnet_bridge.estimate_emissions_local(q)
    assert result["breakdown"]["scope1_detail"].get("fugitive_emissions", 0) > 0


def test_local_estimation_all_scope3_inputs():
    q = {
        "industry": "manufacturing",
        "provided_data": {
            "supplier_spend_usd": 50000,
            "shipping_ton_km": 10000,
            "waste_kg": 500,
            "business_travel_usd": 20000,
            "employee_count": 50,
        },
    }
    result = subnet_bridge.estimate_emissions_local(q)
    s3 = result["breakdown"]["scope3_detail"]
    assert "cat1_purchased_goods" in s3
    assert "cat4_upstream_transport" in s3
    assert "cat5_waste" in s3
    assert "cat6_business_travel" in s3
    assert "cat7_commuting" in s3
