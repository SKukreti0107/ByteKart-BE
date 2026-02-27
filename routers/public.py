from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import nulls_last, desc
from typing import List, Optional
from datetime import datetime, timezone

from db import get_session
from models import Product, Listing, Category, SubCategory, Brand, HeroContent, GlobalNotice

router = APIRouter()


@router.get("/hero")
async def get_active_hero(session: AsyncSession = Depends(get_session)):
    now_str = datetime.now(timezone.utc).isoformat()
    result = await session.execute(
        select(HeroContent).where(HeroContent.is_active == True).order_by(HeroContent.priority)
    )
    all_heroes = result.scalars().all()

    valid_hero = None
    for hero in all_heroes:
        start_valid = not hero.start_date or hero.start_date <= now_str
        end_valid = not hero.end_date or hero.end_date >= now_str
        if start_valid and end_valid:
            valid_hero = hero
            break

    if valid_hero and valid_hero.type != 'newest':
        return valid_hero

    result = await session.execute(
        select(Listing).order_by(nulls_last(desc(Listing.created_at))).limit(5)
    )
    newest_listings = result.scalars().all()
    return {"type": "newest", "listings": newest_listings}


@router.get("/products", response_model=List[Product])
async def list_products(response: Response, session: AsyncSession = Depends(get_session)):
    response.headers["Cache-Control"] = "public, max-age=300"
    result = await session.execute(select(Product))
    return result.scalars().all()


@router.get("/listings", response_model=List[Listing])
async def list_listings(
    response: Response,
    session: AsyncSession = Depends(get_session),
    category_id: Optional[str] = Query(None),
    subCategory_id: Optional[str] = Query(None),
    brand_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(100, le=200),
    offset: int = Query(0, ge=0)
):
    response.headers["Cache-Control"] = "public, max-age=300"
    stmt = select(Listing)
    if category_id:
        stmt = stmt.where(Listing.category_id == category_id)
    if subCategory_id:
        stmt = stmt.where(Listing.subcategory_id == subCategory_id)
    if brand_id:
        stmt = stmt.where(Listing.brand_id == brand_id)
    if search:
        stmt = stmt.where(Listing.name.ilike(f"%{search}%"))
    stmt = stmt.order_by(nulls_last(desc(Listing.created_at)))
    stmt = stmt.offset(offset).limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("/listings/{id}", response_model=Listing)
async def get_listing(id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Listing).where(Listing.id == id))
    listing = result.scalars().first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


@router.get("/categories", response_model=list[Category])
async def list_categories(response: Response, session: AsyncSession = Depends(get_session)):
    response.headers["Cache-Control"] = "public, max-age=300"
    result = await session.execute(select(Category))
    return result.scalars().all()


@router.get("/subCategories", response_model=list[SubCategory])
async def list_sub_categories(
    response: Response,
    session: AsyncSession = Depends(get_session),
    category_id: Optional[str] = Query(None),
):
    response.headers["Cache-Control"] = "public, max-age=300"
    stmt = select(SubCategory)
    if category_id:
        stmt = stmt.where(SubCategory.category_id == category_id)
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("/brands", response_model=List[Brand])
async def list_brands(
    response: Response,
    session: AsyncSession = Depends(get_session),
    subCategory_id: Optional[str] = Query(None)
):
    response.headers["Cache-Control"] = "public, max-age=300"
    stmt = select(Brand)
    if subCategory_id:
        stmt = stmt.join(Listing, Brand.id == Listing.brand_id).where(
            Listing.subcategory_id == subCategory_id
        ).distinct()
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("/notice")
async def get_active_notice(response: Response, session: AsyncSession = Depends(get_session)):
    response.headers["Cache-Control"] = "public, max-age=60"
    result = await session.execute(select(GlobalNotice).where(GlobalNotice.is_active == True).limit(1))
    notice = result.scalars().first()
    if not notice:
        return None
    return notice
