from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List,Optional

from db import init_db, get_session
from models import Product, Listing, Request,Category,SubCategory,Brand, User, HeroContent, ShoppingCart, Order, OrderStatus, CheckoutDetails
from auth import get_current_user, admin_only, get_db_user
from datetime import datetime, timezone

from helpers.verify_payment_sig import get_razorpay_client, verify_payment as verify_razorpay_payment
from helpers.email_service import send_order_confirmation_email, send_order_status_update_email

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
        "http://localhost:3000",
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "null"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    # Since we don't have a created_at field explicitly in Listing, we'll just fetch them reverse order or limit 5
    result = await session.execute(select(Listing).limit(5)) # In a real scenario, order_by(Listing.created_at.desc())
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
    limit: int = Query(40, le=100),
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
    current_user: User = Depends(get_db_user),
    session: AsyncSession = Depends(get_session)
):
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
    razorpay_order = client.order.create({
        "amount": razorpay_amount,
        "currency": "INR",
    })

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

    await session.commit()
    await session.refresh(new_order)

    return razorpay_order

@app.post("/verify/payment")
async def verify_payment_endpoint(
    payment_deets:PaymentsDeets,
    current_user: User = Depends(get_db_user),
    session: AsyncSession = Depends(get_session),
    client=Depends(get_razorpay_client),
):
    is_valid = verify_razorpay_payment(
        razorpay_order_id=payment_deets.razorpay_order_id,
        razorpay_payment_id=payment_deets.razorpay_payment_id,
        razorpay_signature=payment_deets.razorpay_signature,
        client=client
    )
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
                
            await session.commit()

            # Send order confirmation email
            await send_order_confirmation_email(
                user_email=current_user.email,
                user_name=current_user.name or "Customer",
                order_id=str(order.id),
                amount=order.total_amount,
                items=order.items,
                created_at=order.created_at
            )
            
        return {"status": "success", "message": "Payment verified successfully", "order_id": order.id if order else None}
    else:
        raise HTTPException(status_code=400, detail="Signature verification failed")

@app.get("/user/shipping_address")
async def get_user_shipping_address(
    current_user: User = Depends(get_db_user),
    session: AsyncSession = Depends(get_session)
):
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
    current_user: User = Depends(get_db_user),
    session: AsyncSession = Depends(get_session)
):
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
    await session.commit()
    await session.refresh(order)

    # Fetch user to get their email
    user_result = await session.execute(select(User).where(User.id == order.user_id))
    user = user_result.scalars().first()
    if user:
        await send_order_status_update_email(
            user_email=user.email,
            user_name=user.name or "Customer",
            order_id=str(order.id),
            new_status=order.status.value
        )

    return order

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
