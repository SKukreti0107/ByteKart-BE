import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from typing import List
from pydantic import BaseModel
from datetime import datetime, timezone

from db import get_session
from models import (
    User, Listing, Category, SubCategory, Brand, HeroContent,
    Order, OrderStatus, ReturnRequest, ReturnStatus, GlobalNotice,
    SupportTicket, SupportTicketStatus, Request
)
from auth import admin_only
from helpers.email_service import (
    send_order_status_update_email, send_return_status_email,
    send_support_reply_email, send_order_confirmation_email
)

router = APIRouter()


# --- Shared Pydantic models used by admin routes ---

class OrderStatusUpdate(BaseModel):
    status: OrderStatus

class ReturnStatusUpdate(BaseModel):
    status: ReturnStatus

class SupportReplyData(BaseModel):
    reply: str


# --- Listings ---

@router.get("/admin/listings", response_model=List[Listing])
async def admin_list_listings(
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Listing))
    return result.scalars().all()

@router.post("/admin/listing", response_model=Listing)
async def admin_create_listing(
    listing: Listing,
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    session.add(listing)
    await session.commit()
    await session.refresh(listing)
    return listing

@router.put("/admin/listing/{id}", response_model=Listing)
async def admin_update_listing(
    id: str,
    listing_update: Listing,
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Listing).where(Listing.id == id))
    db_listing = result.scalars().first()
    if not db_listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    update_data = listing_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_listing, key, value)
    session.add(db_listing)
    await session.commit()
    await session.refresh(db_listing)
    return db_listing

@router.delete("/admin/listing/{id}")
async def admin_delete_listing(
    id: str,
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Listing).where(Listing.id == id))
    db_listing = result.scalars().first()
    if not db_listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    await session.delete(db_listing)
    await session.commit()
    return {"message": "Listing deleted successfully"}


# --- Categories ---

@router.post("/admin/category", response_model=Category)
async def admin_create_category(
    category: Category,
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    session.add(category)
    await session.commit()
    await session.refresh(category)
    return category

@router.put("/admin/category/{id}", response_model=Category)
async def admin_update_category(
    id: str,
    category_update: Category,
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Category).where(Category.id == id))
    db_cat = result.scalars().first()
    if not db_cat:
        raise HTTPException(status_code=404, detail="Category not found")
    update_data = category_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_cat, key, value)
    session.add(db_cat)
    await session.commit()
    await session.refresh(db_cat)
    return db_cat

@router.delete("/admin/category/{id}")
async def admin_delete_category(
    id: str,
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Category).where(Category.id == id))
    db_cat = result.scalars().first()
    if not db_cat:
        raise HTTPException(status_code=404, detail="Category not found")
    await session.delete(db_cat)
    await session.commit()
    return {"message": "Category deleted successfully"}


# --- Subcategories ---

@router.post("/admin/subcategory", response_model=SubCategory)
async def admin_create_subcategory(
    subcategory: SubCategory,
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    session.add(subcategory)
    await session.commit()
    await session.refresh(subcategory)
    return subcategory

@router.put("/admin/subcategory/{id}", response_model=SubCategory)
async def admin_update_subcategory(
    id: str,
    subcategory_update: SubCategory,
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(SubCategory).where(SubCategory.id == id))
    db_sub = result.scalars().first()
    if not db_sub:
        raise HTTPException(status_code=404, detail="Subcategory not found")
    update_data = subcategory_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_sub, key, value)
    session.add(db_sub)
    await session.commit()
    await session.refresh(db_sub)
    return db_sub

@router.delete("/admin/subcategory/{id}")
async def admin_delete_subcategory(
    id: str,
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(SubCategory).where(SubCategory.id == id))
    db_sub = result.scalars().first()
    if not db_sub:
        raise HTTPException(status_code=404, detail="Subcategory not found")
    await session.delete(db_sub)
    await session.commit()
    return {"message": "Subcategory deleted successfully"}


# --- Brands ---

@router.post("/admin/brand", response_model=Brand)
async def admin_create_brand(
    brand: Brand,
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    session.add(brand)
    await session.commit()
    await session.refresh(brand)
    return brand

@router.put("/admin/brand/{id}", response_model=Brand)
async def admin_update_brand(
    id: str,
    brand_update: Brand,
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Brand).where(Brand.id == id))
    db_brand = result.scalars().first()
    if not db_brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    update_data = brand_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_brand, key, value)
    session.add(db_brand)
    await session.commit()
    await session.refresh(db_brand)
    return db_brand

@router.delete("/admin/brand/{id}")
async def admin_delete_brand(
    id: str,
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Brand).where(Brand.id == id))
    db_brand = result.scalars().first()
    if not db_brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    await session.delete(db_brand)
    await session.commit()
    return {"message": "Brand deleted successfully"}


# --- Hero Content ---

@router.get("/admin/hero", response_model=List[HeroContent])
async def admin_list_hero(
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(HeroContent).order_by(HeroContent.priority))
    return result.scalars().all()

@router.post("/admin/hero", response_model=HeroContent)
async def admin_create_hero(
    hero: HeroContent,
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    session.add(hero)
    await session.commit()
    await session.refresh(hero)
    return hero

@router.put("/admin/hero/{id}", response_model=HeroContent)
async def admin_update_hero(
    id: str,
    hero_update: HeroContent,
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(HeroContent).where(HeroContent.id == id))
    db_hero = result.scalars().first()
    if not db_hero:
        raise HTTPException(status_code=404, detail="Hero content not found")
    update_data = hero_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_hero, key, value)
    session.add(db_hero)
    await session.commit()
    await session.refresh(db_hero)
    return db_hero

@router.delete("/admin/hero/{id}")
async def admin_delete_hero(
    id: str,
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(HeroContent).where(HeroContent.id == id))
    db_hero = result.scalars().first()
    if not db_hero:
        raise HTTPException(status_code=404, detail="Hero content not found")
    await session.delete(db_hero)
    await session.commit()
    return {"message": "Hero content deleted successfully"}


# --- Orders (Admin) ---

@router.get("/admin/orders", response_model=List[Order])
async def admin_get_all_orders(
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Order).order_by(Order.created_at.desc()))
    return result.scalars().all()

@router.put("/admin/orders/{id}/status", response_model=Order)
async def admin_update_order_status(
    id: str,
    update_data: OrderStatusUpdate,
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Order).where(Order.id == id))
    order = result.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = update_data.status
    session.add(order)
    try:
        await session.commit()
        await session.refresh(order)
    except Exception as e:
        await session.rollback()
        logging.error(f"Database error updating order status: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update order status.")

    user_result = await session.execute(select(User).where(User.id == order.user_id))
    user = user_result.scalars().first()
    if user:
        try:
            await send_order_status_update_email(
                user_email=user.email,
                user_name=user.name or "Customer",
                order_id=str(order.id),
                new_status=order.status.value,
                amount=order.total_amount,
                items=order.items
            )
        except Exception as e:
            logging.error(f"Failed to send order status update email: {e}")

    return order


# --- Returns (Admin) ---

@router.get("/admin/returns")
async def admin_get_all_returns(
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(ReturnRequest).order_by(ReturnRequest.created_at.desc()))
    return_requests = result.scalars().all()
    enriched = []
    for rr in return_requests:
        order_result = await session.execute(select(Order).where(Order.id == rr.order_id))
        order = order_result.scalars().first()
        user_result = await session.execute(select(User).where(User.id == rr.user_id))
        user = user_result.scalars().first()
        enriched.append({
            "id": rr.id,
            "order_id": rr.order_id,
            "reason": rr.reason,
            "status": rr.status,
            "created_at": rr.created_at,
            "user_name": user.name if user else None,
            "user_email": user.email if user else None,
            "total_amount": order.total_amount if order else None,
            "order_items": order.items if order else [],
        })
    return enriched

@router.put("/admin/returns/{id}/status")
async def admin_update_return_status(
    id: str,
    update_data: ReturnStatusUpdate,
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(ReturnRequest).where(ReturnRequest.id == id))
    return_req = result.scalars().first()
    if not return_req:
        raise HTTPException(status_code=404, detail="Return request not found")

    return_req.status = update_data.status
    session.add(return_req)

    order_result = await session.execute(select(Order).where(Order.id == return_req.order_id))
    order = order_result.scalars().first()
    if order:
        if update_data.status == ReturnStatus.APPROVED:
            order.status = OrderStatus.RETURNED
        elif update_data.status == ReturnStatus.REJECTED:
            order.status = OrderStatus.DELIVERED
        session.add(order)

    try:
        await session.commit()
        await session.refresh(return_req)
    except Exception as e:
        await session.rollback()
        logging.error(f"Error updating return status: {e}")
        raise HTTPException(status_code=500, detail="Failed to update return status")

    user_result = await session.execute(select(User).where(User.id == return_req.user_id))
    user = user_result.scalars().first()
    if user and order:
        try:
            email_status = "returned" if update_data.status == ReturnStatus.APPROVED else "rejected"
            await send_return_status_email(
                user_email=user.email,
                user_name=user.name or "Customer",
                order_id=str(order.id),
                return_status=email_status,
                amount=order.total_amount,
                items=order.items
            )
        except Exception as e:
            logging.error(f"Failed to send return status email: {e}")

    return return_req


# --- Dashboard Stats ---

@router.get("/admin/dashboard-stats")
async def get_admin_dashboard_stats(
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    products_count = (await session.execute(select(func.count(Listing.id)))).scalar() or 0
    orders_count = (await session.execute(select(func.count(Order.id)))).scalar() or 0
    revenue_result = await session.execute(
        select(func.sum(Order.total_amount))
        .where(Order.status.in_([OrderStatus.PAID, OrderStatus.SHIPPED, OrderStatus.DELIVERED]))
    )
    revenue_sum = revenue_result.scalar() or 0.0
    requests_count = (await session.execute(select(func.count(Request.id)))).scalar() or 0
    open_tickets = (await session.execute(
        select(func.count(SupportTicket.id)).where(SupportTicket.status == SupportTicketStatus.OPEN)
    )).scalar() or 0

    return {
        "totalProducts": products_count,
        "totalOrders": orders_count,
        "revenue": revenue_sum,
        "pendingRequests": requests_count,
        "openTickets": open_tickets
    }


# --- Notices (Admin write) ---

@router.get("/admin/notice")
async def get_all_notices(
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(GlobalNotice).order_by(GlobalNotice.created_at.desc()))
    return result.scalars().all()

@router.post("/admin/notice")
async def create_notice(
    notice_data: GlobalNotice,
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    existing = await session.execute(select(GlobalNotice).where(GlobalNotice.is_active == True))
    for n in existing.scalars().all():
        n.is_active = False
        session.add(n)
    session.add(notice_data)
    await session.commit()
    await session.refresh(notice_data)
    return notice_data

@router.put("/admin/notice/{notice_id}")
async def update_notice(
    notice_id: str,
    notice_data: dict,
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(GlobalNotice).where(GlobalNotice.id == notice_id))
    notice = result.scalars().first()
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    for key, value in notice_data.items():
        if hasattr(notice, key) and key != "id":
            setattr(notice, key, value)
    session.add(notice)
    await session.commit()
    await session.refresh(notice)
    return notice

@router.delete("/admin/notice/{notice_id}")
async def delete_notice(
    notice_id: str,
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(GlobalNotice).where(GlobalNotice.id == notice_id))
    notice = result.scalars().first()
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    await session.delete(notice)
    await session.commit()
    return {"message": "Notice deleted"}


# --- Support (Admin) ---

@router.get("/admin/support")
async def admin_get_all_tickets(
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(SupportTicket).order_by(SupportTicket.created_at.desc()))
    return result.scalars().all()

@router.put("/admin/support/{id}/reply")
async def admin_reply_ticket(
    id: str,
    reply_data: SupportReplyData,
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(SupportTicket).where(SupportTicket.id == id))
    ticket = result.scalars().first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Support ticket not found")

    ticket.admin_reply = reply_data.reply
    ticket.status = SupportTicketStatus.REPLIED
    ticket.replied_at = datetime.now(timezone.utc).isoformat()
    session.add(ticket)

    try:
        await session.commit()
        await session.refresh(ticket)
    except Exception as e:
        await session.rollback()
        logging.error(f"Error updating support ticket: {e}")
        raise HTTPException(status_code=500, detail="Failed to save reply")

    try:
        await send_support_reply_email(
            user_email=ticket.user_email,
            user_name=ticket.user_name,
            original_subject=ticket.subject,
            admin_reply=reply_data.reply,
            ticket_id=ticket.id
        )
    except Exception as e:
        logging.error(f"Failed to send support reply email: {e}")

    return ticket

@router.put("/admin/support/{id}/close")
async def admin_close_ticket(
    id: str,
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(SupportTicket).where(SupportTicket.id == id))
    ticket = result.scalars().first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Support ticket not found")

    ticket.status = SupportTicketStatus.CLOSED
    session.add(ticket)

    try:
        await session.commit()
        await session.refresh(ticket)
    except Exception as e:
        await session.rollback()
        logging.error(f"Error closing support ticket: {e}")
        raise HTTPException(status_code=500, detail="Failed to close ticket")

    return ticket


# --- Test Email ---

@router.post("/test-email")
async def test_email_rendering(email: str = Query(..., description="Email address to send test to")):
    from datetime import datetime, timezone
    from helpers.email_service import send_order_confirmation_email
    items = [
        {"name": "Awesome Product 1", "quantity": 1, "price": 499},
        {"name": "Cool Gadget B", "quantity": 2, "price": 1000}
    ]
    try:
        await send_order_confirmation_email(
            user_email=email,
            user_name="Test User",
            order_id="TEST-ORD-123456",
            amount=2499.0,
            items=items,
            created_at=datetime.now(timezone.utc).isoformat()
        )
        return {"message": f"Test email sent to {email}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
