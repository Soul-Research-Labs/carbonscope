"""AI-powered routes: text parsing, predictions, audit trail, recommendations."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import RATE_LIMIT_DEFAULT
from api.database import get_db
from api.deps import get_current_user
from api.limiter import limiter
from api.models import User
from api.schemas import (
    AuditTrailRequest,
    ParseTextRequest,
    ParseTextResponse,
    PredictionRequest,
    PredictionResponse,
    RecommendationSummary,
)
from api.services import ServiceError
from api.services import ai as ai_svc

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/parse-text", response_model=ParseTextResponse)
@limiter.limit(RATE_LIMIT_DEFAULT)
async def parse_text(
    request: Request,
    body: ParseTextRequest,
    user: User = Depends(get_current_user),
):
    """Parse unstructured text (invoices, bills, etc.) into structured data."""
    extracted = await ai_svc.parse_text(body.text)
    return ParseTextResponse(extracted_data=extracted)


@router.post("/predict", response_model=PredictionResponse)
@limiter.limit(RATE_LIMIT_DEFAULT)
async def predict(
    request: Request,
    body: PredictionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Predict emissions for categories with missing data."""
    prediction = await ai_svc.predict(
        db, user.company_id,
        known_data=body.known_data, industry=body.industry, region=body.region,
    )
    return PredictionResponse(**prediction)


@router.post("/audit-trail")
@limiter.limit(RATE_LIMIT_DEFAULT)
async def audit_trail(
    request: Request,
    body: AuditTrailRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate an audit trail narrative for an emission report."""
    try:
        text = await ai_svc.audit_trail(db, body.report_id, user.company_id)
    except ServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    return {"audit_trail": text}


@router.get("/recommendations/{report_id}", response_model=RecommendationSummary)
@limiter.limit(RATE_LIMIT_DEFAULT)
async def get_recommendations(
    request: Request,
    report_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get carbon reduction recommendations based on a specific report."""
    try:
        data = await ai_svc.recommendations(db, report_id, user.company_id)
    except ServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    return RecommendationSummary(**data)
