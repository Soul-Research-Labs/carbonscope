"""Data marketplace routes — list, browse, and purchase anonymized emission data."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.deps import get_current_user, require_plan
from api.models import User
from api.schemas import (
    DataListingCreate,
    DataListingOut,
    DataPurchaseOut,
    PaginatedResponse,
)
from api.services.marketplace import browse_listings, create_listing, list_my_listings, purchase_listing, withdraw_listing

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


@router.post("/listings", response_model=DataListingOut, status_code=status.HTTP_201_CREATED)
async def create_data_listing(
    body: DataListingCreate,
    user: User = Depends(require_plan("marketplace")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new marketplace listing from one of your reports."""
    try:
        listing = await create_listing(
            db,
            company_id=user.company_id,
            title=body.title,
            description=body.description,
            data_type=body.data_type,
            report_id=body.report_id,
            price_credits=body.price_credits,
        )
        await db.commit()
        await db.refresh(listing)
        return listing
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/listings", response_model=PaginatedResponse[DataListingOut])
async def browse_marketplace(
    industry: str | None = Query(None),
    region: str | None = Query(None),
    data_type: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Browse available marketplace listings."""
    listings, total = await browse_listings(
        db, industry=industry, region=region, data_type=data_type, limit=limit, offset=offset
    )
    return PaginatedResponse(items=listings, total=total, limit=limit, offset=offset)


@router.post("/listings/{listing_id}/purchase", response_model=DataPurchaseOut)
async def purchase_data(
    listing_id: str,
    user: User = Depends(require_plan("marketplace")),
    db: AsyncSession = Depends(get_db),
):
    """Purchase a marketplace listing using credits."""
    try:
        purchase = await purchase_listing(db, listing_id, user.company_id)
        await db.commit()
        # Refresh with relationships loaded
        from sqlalchemy.orm import selectinload
        from sqlalchemy import select
        from api.models import DataPurchase

        result = await db.execute(
            select(DataPurchase)
            .where(DataPurchase.id == purchase.id)
            .options(selectinload(DataPurchase.listing))
        )
        purchase = result.scalar_one()
        return purchase
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/my-listings", response_model=PaginatedResponse[DataListingOut])
async def get_my_listings(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List your own marketplace listings."""
    listings, total = await list_my_listings(db, user.company_id, limit, offset)
    return PaginatedResponse(items=listings, total=total, limit=limit, offset=offset)


@router.post("/listings/{listing_id}/withdraw", response_model=DataListingOut)
async def withdraw_data_listing(
    listing_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Withdraw one of your listings from the marketplace."""
    listing = await withdraw_listing(db, listing_id, user.company_id)
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found or already withdrawn")
    await db.commit()
    await db.refresh(listing)
    return listing
