"""Load and query emission factor JSON datasets with versioning and TTL cache."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any

_logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "emission_factors"

_DATASET_FILES: dict[str, str] = {
    "epa_stationary": "epa_stationary_combustion.json",
    "epa_mobile": "epa_mobile_combustion.json",
    "egrid": "egrid_subregions.json",
    "iea": "iea_grid_factors.json",
    "defra": "defra_factors.json",
    "transport": "transport_factors.json",
    "industry": "industry_averages.json",
    "gwp": "gwp_ar6.json",
}

# TTL cache: {dataset: (data, sha256, loaded_at)}
_cache: dict[str, tuple[dict[str, Any], str, float]] = {}
_CACHE_TTL_SECONDS = 3600  # Re-read datasets after 1 hour


def _file_sha256(path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def load_factors(dataset: str) -> dict[str, Any]:
    """Load a named emission factor dataset from disk with TTL caching.

    Caches parsed JSON for up to ``_CACHE_TTL_SECONDS``.  Re-reads from
    disk when the TTL expires or the file's SHA-256 has changed.

    Parameters
    ----------
    dataset:
        One of: ``epa_stationary``, ``epa_mobile``, ``egrid``, ``iea``,
        ``defra``, ``transport``, ``industry``, ``gwp``.

    Returns
    -------
    dict
        The parsed JSON content.
    """
    filename = _DATASET_FILES.get(dataset)
    if filename is None:
        raise ValueError(
            f"Unknown dataset: {dataset!r}. Available: {sorted(_DATASET_FILES)}"
        )
    path = _DATA_DIR / filename
    now = time.monotonic()

    cached = _cache.get(dataset)
    if cached is not None:
        data, old_sha, loaded_at = cached
        if now - loaded_at < _CACHE_TTL_SECONDS:
            return data
        # TTL expired — check if file changed
        new_sha = _file_sha256(path)
        if new_sha == old_sha:
            _cache[dataset] = (data, old_sha, now)  # refresh TTL
            return data
        _logger.info("Dataset %s changed on disk (sha256=%s→%s), reloading", dataset, old_sha[:12], new_sha[:12])

    with open(path) as f:
        data = json.load(f)
    sha = _file_sha256(path)
    _cache[dataset] = (data, sha, now)
    return data


def get_dataset_version(dataset: str) -> str:
    """Return the SHA-256 hex digest of a dataset file.

    Useful for including dataset provenance in audit trails.
    """
    filename = _DATASET_FILES.get(dataset)
    if filename is None:
        raise ValueError(
            f"Unknown dataset: {dataset!r}. Available: {sorted(_DATASET_FILES)}"
        )
    # Use cached checksum if available
    cached = _cache.get(dataset)
    if cached is not None:
        return cached[1]
    return _file_sha256(_DATA_DIR / filename)


def invalidate_cache(dataset: str | None = None) -> None:
    """Clear the cache for a specific dataset or all datasets.

    Primarily for testing and hot-reload scenarios.
    """
    if dataset is None:
        _cache.clear()
    else:
        _cache.pop(dataset, None)


def get_factor(dataset: str, *keys: str) -> Any:
    """Look up a nested value inside a dataset.

    Example::

        get_factor("epa_stationary", "fuels", "diesel", "total_kgco2e_per_unit")
        # → 2.71

    Raises ``KeyError`` if any key along the path is missing.
    """
    data = load_factors(dataset)
    for key in keys:
        data = data[key]
    return data


# ── Convenience helpers ─────────────────────────────────────────────


def get_fuel_factor(fuel_type: str) -> float:
    """Return kgCO2e per unit for a stationary combustion fuel.

    Falls back to diesel if fuel_type is unrecognised.
    """
    fuels = load_factors("epa_stationary")["fuels"]
    fuel = fuels.get(fuel_type)
    if fuel is None:
        fuel = fuels["diesel"]
    return fuel["total_kgco2e_per_unit"]


def get_grid_factor(region: str) -> float:
    """Return gCO2e/kWh for a region.

    Checks: eGRID subregion → eGRID state lookup → IEA country → global average.
    """
    region_upper = region.upper().strip()

    # 1. Direct eGRID subregion
    egrid = load_factors("egrid")
    if region_upper in egrid["subregions"]:
        return egrid["subregions"][region_upper]["gco2e_per_kwh"]

    # 2. US state → eGRID subregion
    state_map = egrid.get("state_to_subregion", {})
    if region_upper in state_map:
        subregion = state_map[region_upper]
        return egrid["subregions"][subregion]["gco2e_per_kwh"]

    # 3. IEA country code
    iea = load_factors("iea")
    if region_upper in iea["countries"]:
        return iea["countries"][region_upper]["gco2e_per_kwh"]

    # 4. IEA regional average
    if region_upper in iea.get("regional_averages", {}):
        return iea["regional_averages"][region_upper]["gco2e_per_kwh"]

    # 5. Fallback: global average
    return iea["global_average"]["gco2e_per_kwh"]


def get_transport_factor(mode: str, detail: str | None = None) -> float:
    """Return kgCO2e per ton-km for a freight transport mode."""
    transport = load_factors("transport")["freight"]
    mode_data = transport.get(mode)
    if mode_data is None:
        return transport["road"]["kgco2e_per_ton_km"]
    if detail and detail in mode_data:
        return mode_data[detail]
    return mode_data["kgco2e_per_ton_km"]


def get_industry_profile(industry: str) -> dict[str, Any]:
    """Return the industry average profile dict, falling back to manufacturing."""
    industries = load_factors("industry")["industries"]
    if industry not in industries:
        _logger.warning("Unknown industry '%s', falling back to 'manufacturing'", industry)
    return industries.get(industry, industries["manufacturing"])


def log_dataset_versions() -> dict[str, str]:
    """Log and return loaded dataset file sizes / metadata for auditing.

    Called at miner/validator startup to record which factor versions are active.
    """
    versions: dict[str, str] = {}
    for name, filename in _DATASET_FILES.items():
        path = _DATA_DIR / filename
        if path.exists():
            size = path.stat().st_size
            versions[name] = f"{filename} ({size} bytes)"
        else:
            versions[name] = f"{filename} (MISSING)"
    _logger.info("Emission factor datasets loaded: %s", versions)
    return versions
