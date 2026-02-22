from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List,Optional

from db import init_db, get_session
from models import Product, Listing, Request,Category,SubCategory,Brand, User, HeroContent, ShoppingCart
from auth import get_current_user, admin_only, get_db_user
from datetime import datetime, timezone

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(lifespan=lifespan)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://byte-kart.vercel.app",
        "http://localhost:5173",
        "http://localhost:3000",
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
async def list_products(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Product))
    products = result.scalars().all()
    return products

@app.get("/listings", response_model=List[Listing])
async def list_listings(
    session: AsyncSession = Depends(get_session),
    category_id: Optional[str] = Query(None),
    subCategory_id: Optional[str] = Query(None),
    brand_id: Optional[str] = Query(None),
    ):
    stmt = select(Listing)
    if category_id:
        stmt = stmt.where(Listing.category_id == category_id)
    if subCategory_id:
        stmt = stmt.where(Listing.subcategory_id == subCategory_id)
    if brand_id:
        stmt = stmt.where(Listing.brand_id == brand_id)
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
async def list_categories(session:AsyncSession = Depends(get_session)):
    result = await session.execute(select(Category))
    categories = result.scalars().all()
    return categories

@app.get("/subCategories",response_model=list[SubCategory])
async def list_sub_categories(
    session:AsyncSession = Depends(get_session),
    category_id: Optional[str] = Query(None),
    ):
    stmt = select(SubCategory)
    if category_id:
        stmt = stmt.where(SubCategory.category_id == category_id)
    result = await session.execute(stmt)
    sub_categories = result.scalars().all()
    return sub_categories

@app.get("/brands", response_model=List[Brand])
async def list_brands(
    session: AsyncSession = Depends(get_session),
    subCategory_id: Optional[str] = Query(None)
):
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
