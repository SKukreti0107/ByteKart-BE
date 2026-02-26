from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List,Optional
from fastapi.staticfiles import StaticFiles

from db import init_db, get_session
from models import Product, Listing, Request,Category,SubCategory,Brand, User, HeroContent, ShoppingCart, Order, OrderStatus, CheckoutDetails, GlobalNotice, ReturnRequest, ReturnStatus
from auth import get_current_user, admin_only, get_db_user
from datetime import datetime, timezone

from helpers.verify_payment_sig import get_razorpay_client, verify_payment as verify_razorpay_payment
from helpers.email_service import send_order_confirmation_email, send_order_status_update_email, send_email_to_admin, send_return_status_email

import logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(lifespan=lifespan)

# Compression Middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://byte-kart.vercel.app",
        "http://localhost:5173",
        "https://www.bytekart.co.in",
        "null"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/public", StaticFiles(directory="public"), name="public")

@app.get("/")
def read_root():
    return {"message": "Welcome to ByteKart API"}

# --- Public Routes ---

@app.get("/hero")
async def get_active_hero(session: AsyncSession = Depends(get_session)):
    now_str = datetime.now(timezone.utc).isoformat()
    
    # Fetch active hero items, ordered by priority (0 is highest, 10 is default)
    # We will filter dates in Python to keep the SQL query simple, as there won't be many
    result = await session.execute(select(HeroContent).where(HeroContent.is_active == True).order_by(HeroContent.priority))
    all_heroes = result.scalars().all()
    
    valid_hero = None
    for hero in all_heroes:
        # Check date validity
        start_valid = not hero.start_date or hero.start_date <= now_str
        end_valid = not hero.end_date or hero.end_date >= now_str
        if start_valid and end_valid:
            valid_hero = hero
            break

    # If we found a valid hero and it's NOT 'newest' (which means we want dynamic data)
    if valid_hero and valid_hero.type != 'newest':
        return valid_hero
        
    # Fallback to 'newest' behavior: return the top 5 newest listings
    from sqlalchemy import nulls_last, desc
    result = await session.execute(
        select(Listing).order_by(nulls_last(desc(Listing.created_at))).limit(5)
    )
    newest_listings = result.scalars().all()
    
    return {
        "type": "newest",
        "listings": newest_listings
    }

@app.get("/products", response_model=List[Product])
async def list_products(response: Response, session: AsyncSession = Depends(get_session)):
    response.headers["Cache-Control"] = "public, max-age=300"
    result = await session.execute(select(Product))
    products = result.scalars().all()
    return products

@app.get("/listings", response_model=List[Listing])
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
    
    # Always order newest first; NULLS LAST handles existing rows without created_at
    from sqlalchemy import nulls_last, desc
    stmt = stmt.order_by(nulls_last(desc(Listing.created_at)))

    # Appending Limit and Offset
    stmt = stmt.offset(offset).limit(limit)
    
    result = await session.execute(stmt)
    listings = result.scalars().all()
    return listings

@app.get("/listings/{id}", response_model=Listing)
async def get_listing(
    id: str,
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Listing).where(Listing.id == id))
    listing = result.scalars().first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing

@app.get("/categories",response_model=list[Category])
async def list_categories(response: Response, session:AsyncSession = Depends(get_session)):
    response.headers["Cache-Control"] = "public, max-age=300"
    result = await session.execute(select(Category))
    categories = result.scalars().all()
    return categories

@app.get("/subCategories",response_model=list[SubCategory])
async def list_sub_categories(
    response: Response,
    session:AsyncSession = Depends(get_session),
    category_id: Optional[str] = Query(None),
    ):
    response.headers["Cache-Control"] = "public, max-age=300"
    stmt = select(SubCategory)
    if category_id:
        stmt = stmt.where(SubCategory.category_id == category_id)
    result = await session.execute(stmt)
    sub_categories = result.scalars().all()
    return sub_categories

@app.get("/brands", response_model=List[Brand])
async def list_brands(
    response: Response,
    session: AsyncSession = Depends(get_session),
    subCategory_id: Optional[str] = Query(None)
):
    response.headers["Cache-Control"] = "public, max-age=300"
    stmt = select(Brand)
    if subCategory_id:
        stmt = stmt.join(Listing, Brand.id == Listing.brand_id).where(Listing.subcategory_id == subCategory_id).distinct()
    
    result = await session.execute(stmt)
    brands = result.scalars().all()
    return brands
# --- Auth Routes ---

@app.get("/user/me")
def get_current_user_info(current_user: User = Depends(get_db_user)):
    return current_user

# --- Protected Routes ---

@app.post("/requests", response_model=Request)
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

@app.get("/cart", response_model=ShoppingCart)
async def get_user_cart(
    response: Response,
    current_user: User = Depends(get_db_user),
    session: AsyncSession = Depends(get_session)
):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    result = await session.execute(select(ShoppingCart).where(ShoppingCart.user_id == current_user.id))
    cart = result.scalars().first()
    
    # If no cart exists for the user yet, return an empty cart object
    if not cart:
        return ShoppingCart(user_id=current_user.id, items=[])
        
    return cart

@app.put("/cart", response_model=ShoppingCart)
async def update_user_cart(
    cart_update: ShoppingCart,
    current_user: User = Depends(get_db_user),
    session: AsyncSession = Depends(get_session)
):
    # Ensure the user is only updating their own cart
    if str(cart_update.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to update this cart")
        
    result = await session.execute(select(ShoppingCart).where(ShoppingCart.user_id == current_user.id))
    db_cart = result.scalars().first()
    
    if db_cart:
        db_cart.items = cart_update.items
        session.add(db_cart)
    else:
        # Create new cart if it doesn't exist
        db_cart = ShoppingCart(user_id=current_user.id, items=cart_update.items)
        session.add(db_cart)
        
    await session.commit()
    await session.refresh(db_cart)
    return db_cart

from pydantic import BaseModel
from typing import Dict


class OrderData(BaseModel):
    shipping_address: Dict
    shipping_fee: float

class OrderStatusUpdate(BaseModel):
    status: OrderStatus

class PaymentsDeets(BaseModel):
    razorpay_order_id:str
    razorpay_payment_id:str
    razorpay_signature:str


@app.post("/orders")
async def create_order(
    order_data: OrderData,
    current_user: User = Depends(get_db_user),
    session: AsyncSession = Depends(get_session),
    client = Depends(get_razorpay_client)
):
    # Fetch user's cart to calculate the secure total
    result = await session.execute(select(ShoppingCart).where(ShoppingCart.user_id == current_user.id))
    cart = result.scalars().first()
    
    if not cart or not cart.items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    # Securely calculate total amount
    subtotal = sum(item.get('price', 0) * item.get('quantity', 1) for item in cart.items)
    total_amount = subtotal + order_data.shipping_fee

    # Create Razorpay Order (amount in subunits/paise)
    razorpay_amount = int(total_amount * 100)
    try:
        razorpay_order = client.order.create({
            "amount": razorpay_amount,
            "currency": "INR",
        })
    except Exception as e:
        logging.error(f"Razorpay order creation failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Payment gateway error. Please try again.")

    # Save PENDING Order in DB
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

    # Upsert CheckoutDetails
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

    try:
        await session.commit()
        await session.refresh(new_order)
    except Exception as e:
        await session.rollback()
        logging.error(f"Database error saving order: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not process order.")

    return razorpay_order

@app.post("/verify/payment")
async def verify_payment_endpoint(
    payment_deets:PaymentsDeets,
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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Payment verification service error")
    if is_valid:
        # Update order status
        result = await session.execute(select(Order).where(Order.razorpay_order_id == payment_deets.razorpay_order_id))
        order = result.scalars().first()
        if order:
            order.status = OrderStatus.PAID
            order.razorpay_payment_id = payment_deets.razorpay_payment_id
            session.add(order)

            # Clear user cart
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
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Payment validated but failed to update order status.")

            # Send order confirmation email
            try:
                await send_order_confirmation_email(
                    user_email=current_user.email,
                    user_name=current_user.name or "Customer",
                    order_id=str(order.id),
                    amount=order.total_amount,
                    items=order.items,
                    created_at=order.created_at
                )
                await send_email_to_admin("new_order",f"Order {order.id} has been placed",f"Order placed by {current_user.name} for items {', '.join([item['name'] for item in order.items])} and total amount is {order.total_amount}")
            except Exception as e:
                import logging
                logging.error(f"Failed to send order confirmation emails: {e}")
            
        return {"status": "success", "message": "Payment verified successfully", "order_id": order.id if order else None}
    else:
        raise HTTPException(status_code=400, detail="Signature verification failed")

@app.get("/user/shipping_address")
async def get_user_shipping_address(
    response: Response,
    current_user: User = Depends(get_db_user),
    session: AsyncSession = Depends(get_session)
):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    result = await session.execute(
        select(CheckoutDetails).where(CheckoutDetails.user_id == current_user.id)
    )
    details = result.scalars().first()
    if details:
        return {
            "phone": details.phone,
            "address": details.address,
            "city": details.city,
            "pincode": details.pincode
        }
    return {}

@app.get("/orders", response_model=List[Order])
async def get_orders(
    response: Response,
    current_user: User = Depends(get_db_user),
    session: AsyncSession = Depends(get_session)
):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    result = await session.execute(
        select(Order)
        .where(Order.user_id == current_user.id)
        .order_by(Order.created_at.desc())
    )
    return result.scalars().all()

@app.get("/orders/{id}", response_model=Order)
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

@app.get("/razorpay/config")
async def get_razorpay_config():
    import os
    return {"key_id": os.getenv("RAZOR_PAY_KEY_ID")}

# --- Return Routes ---

class ReturnRequestData(BaseModel):
    reason: str

class ReturnStatusUpdate(BaseModel):
    status: ReturnStatus

@app.post("/orders/{id}/return")
async def initiate_return(
    id: str,
    body: ReturnRequestData,
    current_user: User = Depends(get_db_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(Order).where(Order.id == id, Order.user_id == current_user.id)
    )
    order = result.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != OrderStatus.DELIVERED:
        raise HTTPException(status_code=400, detail="Only delivered orders can be returned")

    # Check 7-day window
    order_date = datetime.fromisoformat(order.created_at).replace(tzinfo=timezone.utc)
    days_since = (datetime.now(timezone.utc) - order_date).days
    if days_since > 7:
        raise HTTPException(status_code=400, detail="Return window has expired (7 days from order date)")

    # Check if a return request already exists
    existing = await session.execute(
        select(ReturnRequest).where(ReturnRequest.order_id == id)
    )
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="A return request for this order already exists")

    return_req = ReturnRequest(
        order_id=id,
        user_id=current_user.id,
        reason=body.reason,
    )
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

    # Send return confirmation email to customer
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

# --- Admin Routes ---

@app.get("/admin/listings", response_model=List[Listing])
async def admin_list_listings(
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Listing))
    listings = result.scalars().all()
    return listings

@app.post("/admin/listing", response_model=Listing)
async def admin_create_listing(
    listing: Listing,
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    session.add(listing)
    await session.commit()
    await session.refresh(listing)
    return listing

@app.put("/admin/listing/{id}", response_model=Listing)
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

@app.delete("/admin/listing/{id}")
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

# --- Admin Routes: Categories ---

@app.post("/admin/category", response_model=Category)
async def admin_create_category(
    category: Category,
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    session.add(category)
    await session.commit()
    await session.refresh(category)
    return category

@app.put("/admin/category/{id}", response_model=Category)
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

@app.delete("/admin/category/{id}")
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

# --- Admin Routes: Subcategories ---

@app.post("/admin/subcategory", response_model=SubCategory)
async def admin_create_subcategory(
    subcategory: SubCategory,
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    session.add(subcategory)
    await session.commit()
    await session.refresh(subcategory)
    return subcategory

@app.put("/admin/subcategory/{id}", response_model=SubCategory)
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

@app.delete("/admin/subcategory/{id}")
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

# --- Admin Routes: Brands ---

@app.post("/admin/brand", response_model=Brand)
async def admin_create_brand(
    brand: Brand,
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    session.add(brand)
    await session.commit()
    await session.refresh(brand)
    return brand

@app.put("/admin/brand/{id}", response_model=Brand)
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

@app.delete("/admin/brand/{id}")
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

# --- Admin Routes: Hero Content ---

@app.get("/admin/hero", response_model=List[HeroContent])
async def admin_list_hero(
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(HeroContent).order_by(HeroContent.priority))
    return result.scalars().all()

@app.post("/admin/hero", response_model=HeroContent)
async def admin_create_hero(
    hero: HeroContent,
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    session.add(hero)
    await session.commit()
    await session.refresh(hero)
    return hero

@app.put("/admin/hero/{id}", response_model=HeroContent)
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

@app.delete("/admin/hero/{id}")
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

# --- Admin Routes: Orders ---

@app.get("/admin/orders", response_model=List[Order])
async def admin_get_all_orders(
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Order).order_by(Order.created_at.desc()))
    return result.scalars().all()

@app.put("/admin/orders/{id}/status", response_model=Order)
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

    # Fetch user to get their email
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

# --- Admin Routes: Returns ---

@app.get("/admin/returns")
async def admin_get_all_returns(
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(ReturnRequest).order_by(ReturnRequest.created_at.desc())
    )
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

@app.put("/admin/returns/{id}/status")
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

    # Update the linked order status accordingly
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

    # Notify customer by email using the return-specific template
    user_result = await session.execute(select(User).where(User.id == return_req.user_id))
    user = user_result.scalars().first()
    if user and order:
        try:
            # Map the return decision to the right email status
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



# --- Admin Dashboard Stats ---
@app.get("/admin/dashboard-stats")
async def get_admin_dashboard_stats(
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    from sqlalchemy import func
    
    # Total Products (Listings)
    products_count = (await session.execute(select(func.count(Listing.id)))).scalar() or 0
    
    # Total Orders
    orders_count = (await session.execute(select(func.count(Order.id)))).scalar() or 0
    
    # Total Revenue (sum of total_amount where status is paid, shipped, or delivered)
    revenue_result = await session.execute(
        select(func.sum(Order.total_amount))
        .where(Order.status.in_([OrderStatus.PAID, OrderStatus.SHIPPED, OrderStatus.DELIVERED]))
    )
    revenue_sum = revenue_result.scalar() or 0.0
    
    # Pending Requests
    requests_count = (await session.execute(select(func.count(Request.id)))).scalar() or 0
    
    return {
        "totalProducts": products_count,
        "totalOrders": orders_count,
        "revenue": revenue_sum,
        "pendingRequests": requests_count
    }

# --- Test Email ---
@app.post("/test-email")
async def test_email_rendering(email: str = Query(..., description="Email address to send test to")):
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

# --- Global Notice ---

@app.get("/notice")
async def get_active_notice(response: Response, session: AsyncSession = Depends(get_session)):
    response.headers["Cache-Control"] = "public, max-age=60"
    result = await session.execute(select(GlobalNotice).where(GlobalNotice.is_active == True).limit(1))
    notice = result.scalars().first()
    if not notice:
        return None
    return notice

@app.get("/admin/notice")
async def get_all_notices(
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(GlobalNotice).order_by(GlobalNotice.created_at.desc()))
    notices = result.scalars().all()
    return notices

@app.post("/admin/notice")
async def create_notice(
    notice_data: GlobalNotice,
    current_user: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session)
):
    # Deactivate all existing notices
    existing = await session.execute(select(GlobalNotice).where(GlobalNotice.is_active == True))
    for n in existing.scalars().all():
        n.is_active = False
        session.add(n)
    
    session.add(notice_data)
    await session.commit()
    await session.refresh(notice_data)
    return notice_data

@app.put("/admin/notice/{notice_id}")
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

@app.delete("/admin/notice/{notice_id}")
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
