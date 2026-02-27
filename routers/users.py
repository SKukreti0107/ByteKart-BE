from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
from models import User, Request, ShoppingCart
from auth import get_db_user

router = APIRouter()


@router.get("/user/me")
def get_current_user_info(current_user: User = Depends(get_db_user)):
    return current_user


@router.post("/requests", response_model=Request)
async def create_request(
    request_data: Request,
    current_user: User = Depends(get_db_user),
    session: AsyncSession = Depends(get_session)
):
    request_data.user_id = current_user.id
    session.add(request_data)
    await session.commit()
    await session.refresh(request_data)
    return request_data


@router.get("/cart", response_model=ShoppingCart)
async def get_user_cart(
    response: Response,
    current_user: User = Depends(get_db_user),
    session: AsyncSession = Depends(get_session)
):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    result = await session.execute(select(ShoppingCart).where(ShoppingCart.user_id == current_user.id))
    cart = result.scalars().first()
    if not cart:
        return ShoppingCart(user_id=current_user.id, items=[])
    return cart


@router.put("/cart", response_model=ShoppingCart)
async def update_user_cart(
    cart_update: ShoppingCart,
    current_user: User = Depends(get_db_user),
    session: AsyncSession = Depends(get_session)
):
    if str(cart_update.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to update this cart")

    result = await session.execute(select(ShoppingCart).where(ShoppingCart.user_id == current_user.id))
    db_cart = result.scalars().first()

    if db_cart:
        db_cart.items = cart_update.items
        session.add(db_cart)
    else:
        db_cart = ShoppingCart(user_id=current_user.id, items=cart_update.items)
        session.add(db_cart)

    await session.commit()
    await session.refresh(db_cart)
    return db_cart
