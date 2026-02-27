import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import datetime, timezone

from db import get_session
from models import User, Order, OrderStatus, ReturnRequest, ReturnStatus
from auth import get_db_user
from helpers.email_service import send_email_to_admin, send_return_status_email

router = APIRouter()


class ReturnRequestData(BaseModel):
    reason: str


@router.post("/orders/{id}/return")
async def initiate_return(
    id: str,
    body: ReturnRequestData,
    current_user: User = Depends(get_db_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Order).where(Order.id == id, Order.user_id == current_user.id))
    order = result.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != OrderStatus.DELIVERED:
        raise HTTPException(status_code=400, detail="Only delivered orders can be returned")

    order_date = datetime.fromisoformat(order.created_at).replace(tzinfo=timezone.utc)
    days_since = (datetime.now(timezone.utc) - order_date).days
    if days_since > 7:
        raise HTTPException(status_code=400, detail="Return window has expired (7 days from order date)")

    existing = await session.execute(select(ReturnRequest).where(ReturnRequest.order_id == id))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="A return request for this order already exists")

    return_req = ReturnRequest(order_id=id, user_id=current_user.id, reason=body.reason)
    session.add(return_req)
    order.status = OrderStatus.RETURN_REQUESTED
    session.add(order)

    try:
        await session.commit()
        await session.refresh(return_req)
    except Exception as e:
        await session.rollback()
        logging.error(f"Error saving return request: {e}")
        raise HTTPException(status_code=500, detail="Could not save return request")

    try:
        await send_email_to_admin(
            "return_request",
            f"Return Request for Order {id}",
            f"Customer {current_user.name or current_user.email} has requested a return for order {id}.\nReason: {body.reason}"
        )
    except Exception as e:
        logging.error(f"Failed to send return request admin email: {e}")

    try:
        await send_return_status_email(
            user_email=current_user.email,
            user_name=current_user.name or "Customer",
            order_id=str(order.id),
            return_status="return_requested",
            amount=order.total_amount,
            items=order.items
        )
    except Exception as e:
        logging.error(f"Failed to send return confirmation email: {e}")

    return {"message": "Return request submitted successfully", "return_request_id": return_req.id}
