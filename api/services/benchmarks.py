"""Benchmark service — industry comparison logic."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import Company, EmissionReport, IndustryBenchmark


class BenchmarkError(Exception):
    """Domain error raised by benchmark operations."""

    def __init__(self, detail: str, *, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code


def _pct_diff(company_val: float, avg_val: float) -> float:
    if avg_val == 0:
        return 0.0
    return round((company_val - avg_val) / avg_val * 100, 1)


def _rank_label(pct_diff: float) -> str:
    if pct_diff <= -30:
        return "top_10"
    if pct_diff <= -10:
        return "top_25"
    if pct_diff <= 10:
        return "median"
    if pct_diff <= 30:
        return "bottom_25"
    return "bottom_10"


async def compare_to_industry(
    db: AsyncSession,
    report_id: str,
    company_id: str,
) -> dict:
    """Compare a company's emission report against the industry benchmark.

    Returns a dict with company_emissions, industry_average, percentile_rank, vs_average.
    Raises BenchmarkError if report not found.
    """
    result = await db.execute(
        select(EmissionReport).where(
            EmissionReport.id == report_id,
            EmissionReport.company_id == company_id,
            EmissionReport.deleted_at.is_(None),
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise BenchmarkError("Report not found", status_code=404)

    company_result = await db.execute(select(Company).where(Company.id == company_id))
    company = company_result.scalar_one()

    bench_result = await db.execute(
        select(IndustryBenchmark).where(
            IndustryBenchmark.industry == company.industry,
            IndustryBenchmark.year == report.year,
        ).order_by(
            (IndustryBenchmark.region == company.region).desc(),
        ).limit(1)
    )
    benchmark = bench_result.scalar_one_or_none()

    company_emissions = {
        "scope1": report.scope1,
        "scope2": report.scope2,
        "scope3": report.scope3,
        "total": report.total,
    }

    if benchmark is None:
        return {
            "company_emissions": company_emissions,
            "industry_average": None,
            "percentile_rank": {"scope1": None, "scope2": None, "scope3": None, "total": None},
            "vs_average": {"scope1": None, "scope2": None, "scope3": None, "total": None},
        }

    vs = {
        "scope1": _pct_diff(report.scope1, benchmark.avg_scope1_tco2e),
        "scope2": _pct_diff(report.scope2, benchmark.avg_scope2_tco2e),
        "scope3": _pct_diff(report.scope3, benchmark.avg_scope3_tco2e),
        "total": _pct_diff(report.total, benchmark.avg_total_tco2e),
    }

    ranks = {k: _rank_label(v) for k, v in vs.items()}

    return {
        "company_emissions": company_emissions,
        "industry_average": benchmark,
        "percentile_rank": ranks,
        "vs_average": vs,
    }
