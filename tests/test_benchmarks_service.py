"""Unit tests for api/services/benchmarks.py — benchmark comparison logic."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import Company, EmissionReport, IndustryBenchmark
from api.services.benchmarks import BenchmarkError, compare_to_industry, _pct_diff, _rank_label


# ── Pure function tests ──────────────────────────────────────────────


class TestPctDiff:
    def test_positive_diff(self):
        assert _pct_diff(150.0, 100.0) == 50.0

    def test_negative_diff(self):
        assert _pct_diff(70.0, 100.0) == -30.0

    def test_zero_avg(self):
        assert _pct_diff(100.0, 0.0) == 0.0

    def test_equal(self):
        assert _pct_diff(100.0, 100.0) == 0.0


class TestRankLabel:
    def test_top_10(self):
        assert _rank_label(-35.0) == "top_10"

    def test_top_25(self):
        assert _rank_label(-15.0) == "top_25"

    def test_median(self):
        assert _rank_label(5.0) == "median"

    def test_bottom_25(self):
        assert _rank_label(25.0) == "bottom_25"

    def test_bottom_10(self):
        assert _rank_label(50.0) == "bottom_10"

    def test_boundary_top_10(self):
        assert _rank_label(-30.0) == "top_10"

    def test_boundary_top_25(self):
        assert _rank_label(-10.0) == "top_25"


# ── Integration tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_compare_report_not_found(auth_client: AsyncClient):
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        result = await db.execute(select(Company))
        company = result.scalars().first()
        with pytest.raises(BenchmarkError, match="Report not found"):
            await compare_to_industry(db, "nonexistent", company.id)


@pytest.mark.asyncio
async def test_compare_no_benchmark(auth_client: AsyncClient):
    """When no benchmark exists, should return None for industry_average."""
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        result = await db.execute(select(Company))
        company = result.scalars().first()

        report = EmissionReport(
            company_id=company.id, year=2025,
            scope1=100, scope2=200, scope3=300, total=600, confidence=0.8,
        )
        db.add(report)
        await db.commit()

        result = await compare_to_industry(db, report.id, company.id)
        assert result["industry_average"] is None
        assert result["company_emissions"]["total"] == 600


@pytest.mark.asyncio
async def test_compare_with_benchmark(auth_client: AsyncClient):
    """When benchmark exists, should compute vs_average and rank."""
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        result = await db.execute(select(Company))
        company = result.scalars().first()

        report = EmissionReport(
            company_id=company.id, year=2025,
            scope1=50, scope2=100, scope3=150, total=300, confidence=0.8,
        )
        db.add(report)

        benchmark = IndustryBenchmark(
            industry=company.industry, region=company.region, year=2025,
            avg_scope1_tco2e=100, avg_scope2_tco2e=200,
            avg_scope3_tco2e=300, avg_total_tco2e=600,
            sample_size=50,
        )
        db.add(benchmark)
        await db.commit()

        result = await compare_to_industry(db, report.id, company.id)
        assert result["industry_average"] is not None
        assert result["vs_average"]["total"] == -50.0  # 300 is 50% below 600
        assert result["percentile_rank"]["total"] == "top_10"  # -50% -> top_10
