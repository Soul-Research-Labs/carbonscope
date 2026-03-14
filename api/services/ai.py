"""AI service — DB lookups + delegation to AI sub-services."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import Company, EmissionReport
from api.services import ServiceError
from api.services.llm_parser import generate_audit_trail, parse_unstructured_text
from api.services.prediction import predict_missing_emissions
from api.services.recommendations import generate_recommendations, summarize_reduction_potential


async def _get_company(db: AsyncSession, company_id: str) -> Company:
    result = await db.execute(select(Company).where(Company.id == company_id))
    return result.scalar_one()


async def _get_report(db: AsyncSession, report_id: str, company_id: str) -> EmissionReport:
    result = await db.execute(
        select(EmissionReport).where(
            EmissionReport.id == report_id,
            EmissionReport.company_id == company_id,
            EmissionReport.deleted_at.is_(None),
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise ServiceError("Report not found", status_code=404)
    return report


async def parse_text(text: str) -> dict:
    return await parse_unstructured_text(text)


async def predict(
    db: AsyncSession,
    company_id: str,
    *,
    known_data: dict,
    industry: str | None = None,
    region: str | None = None,
) -> dict:
    company = await _get_company(db, company_id)
    return predict_missing_emissions(
        known_data,
        industry or company.industry,
        region or company.region,
    )


async def audit_trail(
    db: AsyncSession, report_id: str, company_id: str,
) -> str:
    report = await _get_report(db, report_id, company_id)
    company = await _get_company(db, company_id)
    return await generate_audit_trail(
        company=company.name,
        industry=company.industry,
        year=report.year,
        scope1=report.scope1,
        scope2=report.scope2,
        scope3=report.scope3,
        total=report.total,
        breakdown=report.breakdown,
        assumptions=report.assumptions,
        sources=report.sources,
        confidence=report.confidence,
    )


async def recommendations(
    db: AsyncSession, report_id: str, company_id: str,
) -> dict[str, Any]:
    report = await _get_report(db, report_id, company_id)
    company = await _get_company(db, company_id)

    emissions = {
        "scope1": report.scope1,
        "scope2": report.scope2,
        "scope3": report.scope3,
        "total": report.total,
    }
    recs = generate_recommendations(
        emissions=emissions,
        breakdown=report.breakdown,
        industry=company.industry,
    )
    summary = summarize_reduction_potential(recs, report.total)
    return {"recommendations": recs, "summary": summary}
