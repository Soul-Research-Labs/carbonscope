"""CarbonSynapse — the Bittensor protocol for carbon emission estimation.

Defines the request/response contract between validators (who send company
questionnaires) and miners (who return Scope 1/2/3 emission estimates).
"""

from __future__ import annotations

import hashlib
import json
from typing import ClassVar, Optional

import bittensor as bt
from pydantic import field_validator


class CarbonSynapse(bt.Synapse):
    """Bittensor Synapse for corporate carbon footprint estimation.

    **Validator → Miner (request):**
        ``questionnaire`` and ``context`` are populated by the validator.

    **Miner → Validator (response):**
        The miner fills ``emissions``, ``breakdown``, ``confidence``,
        ``data_completeness``, ``sources``, ``assumptions``, and
        ``methodology_version``.
    """

    # Protocol version — bumped on breaking changes to request/response shape
    PROTOCOL_VERSION: ClassVar[int] = 2

    # ── Request fields (validator fills these) ──────────────────────

    protocol_version: int = 2
    """Protocol version of this synapse.  Validators and miners can use this
    to detect incompatible peers and gracefully degrade."""

    questionnaire: dict = {}
    """Company data.  Expected keys:

    - ``company`` (str): Company name / ID.
    - ``industry`` (str): Sector key — ``"manufacturing"``, ``"transportation"``,
      ``"technology"``, ``"retail"``, ``"energy"``, ``"financial_services"``,
      ``"construction"``, ``"food_beverage"``, ``"healthcare"``.
    - ``services_used`` (list[str]): Business activities.
    - ``provided_data`` (dict): Partial operational data:
        - ``fuel_use_liters`` (float)
        - ``fuel_type`` (str)
        - ``natural_gas_m3`` (float)
        - ``electricity_kwh`` (float)
        - ``vehicle_km`` (float)
        - ``employee_count`` (int)
        - ``revenue_usd`` (float)
        - ``supplier_spend_usd`` (float)
        - ``shipping_ton_km`` (float)
        - ``office_sqm`` (float)
        - ``business_travel_usd`` (float)
        - ``waste_kg`` (float)
        - ``refrigerant_type`` (str)
        - ``refrigerant_kg_leaked`` (float)
        - ``rec_kwh`` (float)
    - ``region`` (str): ISO-2 country code, US state, or eGRID subregion.
    - ``year`` (int): Reporting year.
    """

    context: dict = {}
    """Additional context.  Expected keys:

    - ``grid_factor_override`` (float | None): Supplier-specific gCO2e/kWh.
    - ``methodology`` (str): ``"ghg_protocol"`` (default).
    """

    # ── Response fields (miner fills these) ─────────────────────────

    emissions: Optional[dict] = None
    """Top-level emission totals in kgCO2e::

        {"scope1": float, "scope2": float, "scope3": float, "total": float}
    """

    breakdown: Optional[dict] = None
    """Category-level breakdown::

        {
            "scope1_detail": {"stationary_combustion": float, "mobile_combustion": float, ...},
            "scope2_detail": {"location_based": float, "market_based": float},
            "scope3_detail": {"cat1_purchased_goods": float, "cat4_upstream_transport": float, ...}
        }
    """

    confidence: Optional[float] = None
    """Data-completeness-based confidence score (0.0–1.0)."""

    data_completeness: Optional[float] = None
    """Fraction of expected data fields that were provided (0.0–1.0)."""

    sources: Optional[list] = None
    """List of data sources used (e.g. ``["EPA emission factors v2025", ...]``)."""

    assumptions: Optional[list] = None
    """Audit trail: list of assumptions made during estimation."""

    methodology_version: Optional[str] = None
    """Methodology identifier (e.g. ``"ghg_protocol_v2025"``)."""

    request_hash: Optional[str] = None
    """SHA-256 hash of the questionnaire + emissions, set by the miner as proof
    of computation.  Validators can verify: ``sha256(json(questionnaire) + json(emissions))``."""

    def compute_request_hash(self) -> str:
        """Compute the SHA-256 hash binding the request to the response.

        Includes protocol version as a prefix byte so hash schemes can evolve.
        """
        version_prefix = f"v{self.protocol_version}:"
        payload = version_prefix + json.dumps(self.questionnaire, sort_keys=True) + json.dumps(
            self.emissions, sort_keys=True, default=str
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    # ── Field validators ────────────────────────────────────────────

    @field_validator("confidence")
    @classmethod
    def clamp_confidence(cls, v: float | None) -> float | None:
        if v is not None and v >= 0:
            return max(0.0, min(v, 1.0))
        return v  # Negative values are error codes (-1.0, -2.0)

    @field_validator("emissions")
    @classmethod
    def check_emissions(cls, v: dict | None) -> dict | None:
        if v is not None:
            cleaned = dict(v)
            for key in ("scope1", "scope2", "scope3", "total"):
                val = cleaned.get(key)
                if val is not None and val < 0:
                    cleaned[key] = 0.0
            return cleaned
        return v

    @field_validator("breakdown")
    @classmethod
    def check_breakdown_keys(cls, v: dict | None) -> dict | None:
        if v is not None:
            allowed = {"scope1_detail", "scope2_detail", "scope3_detail"}
            return {k: val for k, val in v.items() if k in allowed}
        return v

    # ── Synapse config ──────────────────────────────────────────────

    required_hash_fields: ClassVar[tuple[str, ...]] = ("questionnaire",)
