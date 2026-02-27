from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from db import get_session
from models import User, RedeemCode
from auth import get_db_user, admin_only

router = APIRouter()


class RedeemCodeValidation(BaseModel):
    code: str


@router.post("/redeem-code/validate")
async def validate_redeem_code(
    body: RedeemCodeValidation,
    current_user: User = Depends(get_db_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(RedeemCode).where(RedeemCode.code == body.code.strip().upper())
    )
    redeem = result.scalars().first()
    if not redeem or not redeem.is_active:
        raise HTTPException(status_code=400, detail="Invalid redeem code")
    if redeem.times_redeemed >= redeem.max_redeems:
        raise HTTPException(status_code=400, detail="This code has reached its maximum number of uses")
    return {
        "code": redeem.code,
        "discount_type": redeem.discount_type,
        "discount_value": redeem.discount_value,
        "remaining_uses": redeem.max_redeems - redeem.times_redeemed
    }


@router.get("/admin/redeem-codes")
async def admin_list_redeem_codes(
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(RedeemCode).order_by(RedeemCode.created_at.desc()))
    return result.scalars().all()


@router.post("/admin/redeem-codes")
async def admin_create_redeem_code(
    code_data: RedeemCode,
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    code_data.code = code_data.code.strip().upper()
    existing = await session.execute(select(RedeemCode).where(RedeemCode.code == code_data.code))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="A code with this name already exists")
    session.add(code_data)
    await session.commit()
    await session.refresh(code_data)
    return code_data


@router.put("/admin/redeem-codes/{id}")
async def admin_update_redeem_code(
    id: str,
    update_data: dict,
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(RedeemCode).where(RedeemCode.id == id))
    redeem = result.scalars().first()
    if not redeem:
        raise HTTPException(status_code=404, detail="Redeem code not found")
    for key, value in update_data.items():
        if hasattr(redeem, key) and key != "id":
            if key == "code":
                value = value.strip().upper()
            setattr(redeem, key, value)
    session.add(redeem)
    await session.commit()
    await session.refresh(redeem)
    return redeem


@router.delete("/admin/redeem-codes/{id}")
async def admin_delete_redeem_code(
    id: str,
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(RedeemCode).where(RedeemCode.id == id))
    redeem = result.scalars().first()
    if not redeem:
        raise HTTPException(status_code=404, detail="Redeem code not found")
    await session.delete(redeem)
    await session.commit()
    return {"message": "Redeem code deleted successfully"}
