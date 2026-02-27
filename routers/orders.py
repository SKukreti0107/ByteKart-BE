import os
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from pydantic import BaseModel
from typing import Dict, Optional

from db import get_session
from models import User, ShoppingCart, Order, OrderStatus, CheckoutDetails, RedeemCode
from auth import get_db_user
from helpers.verify_payment_sig import get_razorpay_client, verify_payment as verify_razorpay_payment
from helpers.email_service import send_order_confirmation_email, send_email_to_admin

router = APIRouter()


class OrderData(BaseModel):
    shipping_address: Dict
    shipping_fee: float
    redeem_code: Optional[str] = None


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class PaymentsDeets(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


@router.post("/orders")
async def create_order(
    order_data: OrderData,
    current_user: User = Depends(get_db_user),
    session: AsyncSession = Depends(get_session),
    client=Depends(get_razorpay_client)
):
    result = await session.execute(select(ShoppingCart).where(ShoppingCart.user_id == current_user.id))
    cart = result.scalars().first()

    if not cart or not cart.items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    subtotal = sum(item.get('price', 0) * item.get('quantity', 1) for item in cart.items)
    discount = 0.0
    applied_redeem_code = None

    if order_data.redeem_code:
        code_result = await session.execute(
            select(RedeemCode).where(RedeemCode.code == order_data.redeem_code.strip().upper())
        )
        redeem = code_result.scalars().first()
        if not redeem or not redeem.is_active or redeem.times_redeemed >= redeem.max_redeems:
            raise HTTPException(status_code=400, detail="Invalid or expired redeem code")
        if redeem.discount_type == "percentage":
            discount = round(subtotal * (redeem.discount_value / 100), 2)
        else:
            discount = min(redeem.discount_value, subtotal)
        applied_redeem_code = redeem

    total_amount = max(subtotal - discount + order_data.shipping_fee, 0)
    razorpay_amount = int(total_amount * 100)

    try:
        razorpay_order = client.order.create({"amount": razorpay_amount, "currency": "INR"})
    except Exception as e:
        logging.error(f"Razorpay order creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment gateway error. Please try again."
        )

    new_order = Order(
        user_id=current_user.id,
        razorpay_order_id=razorpay_order["id"],
        items=cart.items,
        shipping_address=order_data.shipping_address,
        shipping_fee=order_data.shipping_fee,
        total_amount=total_amount,
        status=OrderStatus.PENDING
    )
    session.add(new_order)

    db_details = await session.execute(select(CheckoutDetails).where(CheckoutDetails.user_id == current_user.id))
    detail = db_details.scalars().first()
    address_data = order_data.shipping_address
    if not detail:
        detail = CheckoutDetails(user_id=current_user.id)
    detail.phone = address_data.get('phone', detail.phone)
    detail.address = address_data.get('address', detail.address)
    detail.city = address_data.get('city', detail.city)
    detail.pincode = address_data.get('pincode', detail.pincode)
    session.add(detail)

    if applied_redeem_code:
        applied_redeem_code.times_redeemed += 1
        session.add(applied_redeem_code)

    try:
        await session.commit()
        await session.refresh(new_order)
    except Exception as e:
        await session.rollback()
        logging.error(f"Database error saving order: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not process order."
        )

    return razorpay_order


@router.post("/verify/payment")
async def verify_payment_endpoint(
    payment_deets: PaymentsDeets,
    current_user: User = Depends(get_db_user),
    session: AsyncSession = Depends(get_session),
    client=Depends(get_razorpay_client),
):
    try:
        is_valid = verify_razorpay_payment(
            razorpay_order_id=payment_deets.razorpay_order_id,
            razorpay_payment_id=payment_deets.razorpay_payment_id,
            razorpay_signature=payment_deets.razorpay_signature,
            client=client
        )
    except Exception as e:
        logging.error(f"Razorpay verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment verification service error"
        )

    if is_valid:
        result = await session.execute(select(Order).where(Order.razorpay_order_id == payment_deets.razorpay_order_id))
        order = result.scalars().first()
        if order:
            order.status = OrderStatus.PAID
            order.razorpay_payment_id = payment_deets.razorpay_payment_id
            session.add(order)

            cart_result = await session.execute(select(ShoppingCart).where(ShoppingCart.user_id == current_user.id))
            cart = cart_result.scalars().first()
            if cart:
                cart.items = []
                session.add(cart)

            try:
                await session.commit()
            except Exception as e:
                await session.rollback()
                logging.error(f"Database error during payment validation for Order {order.id}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Payment validated but failed to update order status."
                )

            try:
                await send_order_confirmation_email(
                    user_email=current_user.email,
                    user_name=current_user.name or "Customer",
                    order_id=str(order.id),
                    amount=order.total_amount,
                    items=order.items,
                    created_at=order.created_at
                )
                await send_email_to_admin(
                    "new_order",
                    f"Order {order.id} has been placed",
                    f"Order placed by {current_user.name} for items {', '.join([item['name'] for item in order.items])} and total amount is {order.total_amount}"
                )
            except Exception as e:
                logging.error(f"Failed to send order confirmation emails: {e}")

        return {"status": "success", "message": "Payment verified successfully", "order_id": order.id if order else None}
    else:
        raise HTTPException(status_code=400, detail="Signature verification failed")


@router.get("/user/shipping_address")
async def get_user_shipping_address(
    response: Response,
    current_user: User = Depends(get_db_user),
    session: AsyncSession = Depends(get_session)
):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    result = await session.execute(select(CheckoutDetails).where(CheckoutDetails.user_id == current_user.id))
    details = result.scalars().first()
    if details:
        return {
            "phone": details.phone,
            "address": details.address,
            "city": details.city,
            "pincode": details.pincode
        }
    return {}


@router.get("/orders", response_model=List[Order])
async def get_orders(
    response: Response,
    current_user: User = Depends(get_db_user),
    session: AsyncSession = Depends(get_session)
):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    result = await session.execute(
        select(Order).where(Order.user_id == current_user.id).order_by(Order.created_at.desc())
    )
    return result.scalars().all()


@router.get("/orders/{id}", response_model=Order)
async def get_order(
    id: str,
    current_user: User = Depends(get_db_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Order).where(Order.id == id, Order.user_id == current_user.id))
    order = result.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.get("/razorpay/config")
async def get_razorpay_config():
    return {"key_id": os.getenv("RAZOR_PAY_KEY_ID")}
