import asyncio
import sys
import os
from uuid import uuid4

# Add the parent directory to sys.path to import from db and models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import select
from db import async_session_maker
from models import Listing, Category, SubCategory, Brand, StockStatus, ItemStatus

async def seed_listings():
    # Sample listings data
    listings_to_seed = [
        {
            "name": "Razer Blade 15 Gaming Laptop",
            "supplier_id": str(uuid4()),
            "category_name": "Laptops",
            "subcategory_name": "Gaming Laptops",
            "brand_name": "Razer",
            "price": 2499.99,
            "stock_status": StockStatus.IN_STOCK,
            "item_status": ItemStatus.NEW,
            "description": "High-performance gaming laptop with NVIDIA RTX 3080.",
            "image_url": "https://m.media-amazon.com/images/I/71wF7Y6nSdL._AC_SL1500_.jpg"
        },
        {
            "name": "iPhone 15 Pro Max - 256GB",
            "supplier_id": str(uuid4()),
            "category_name": "Smartphones",
            "subcategory_name": "iPhones",
            "brand_name": "Apple",
            "price": 1199.00,
            "stock_status": StockStatus.IN_STOCK,
            "item_status": ItemStatus.NEW,
            "description": "The latest iPhone with Titanium design and A17 Pro chip.",
            "image_url": "https://m.media-amazon.com/images/I/81SigAnNfKL._AC_SL1500_.jpg"
        },
        {
            "name": "Dell UltraSharp 27 4K Monitor",
            "supplier_id": str(uuid4()),
            "category_name": "Monitors",
            "subcategory_name": "4K Monitors",
            "brand_name": "Dell",
            "price": 549.99,
            "stock_status": StockStatus.LOW_STOCK,
            "item_status": ItemStatus.OPEN_BOX,
            "description": "Excellent color accuracy for professionals.",
            "image_url": "https://m.media-amazon.com/images/I/71Y8X-X-f-L._AC_SL1500_.jpg"
        },
        {
            "name": "Sony WH-1000XM5 Wireless Headphones",
            "supplier_id": str(uuid4()),
            "category_name": "Audio",
            "subcategory_name": "Headphones",
            "brand_name": "Sony",
            "price": 348.00,
            "stock_status": StockStatus.IN_STOCK,
            "item_status": ItemStatus.NEW,
            "description": "Industry-leading noise canceling with exceptional sound.",
            "image_url": "https://m.media-amazon.com/images/I/51SKmu2G9FL._AC_SL1500_.jpg"
        },
        {
            "name": "Samsung Galaxy Tab S9 Ultra",
            "supplier_id": str(uuid4()),
            "category_name": "Tablets",
            "subcategory_name": "Android Tablets",
            "brand_name": "Samsung",
            "price": 1099.99,
            "stock_status": StockStatus.OUT_OF_STOCK,
            "item_status": ItemStatus.NEW,
            "description": "Large AMOLED display with S-Pen included.",
            "image_url": "https://m.media-amazon.com/images/I/71vstS-6iXL._AC_SL1500_.jpg"
        },
        {
            "name": "Logitech G Pro X Superlight",
            "supplier_id": str(uuid4()),
            "category_name": "Gaming",
            "subcategory_name": "Gaming Mice",
            "brand_name": "Logitech",
            "price": 129.99,
            "stock_status": StockStatus.IN_STOCK,
            "item_status": ItemStatus.NEW,
            "description": "Ultra-lightweight wireless gaming mouse.",
            "image_url": "https://m.media-amazon.com/images/I/51SKmu2G9FL._AC_SL1500_.jpg"
        }
    ]

    async with async_session_maker() as session:
        for data in listings_to_seed:
            # Check if listing with the same name already exists
            statement = select(Listing).where(Listing.name == data["name"])
            result = await session.execute(statement)
            existing_listing = result.scalars().first()

            if not existing_listing:
                # Resolve Category
                cat_stmt = select(Category).where(Category.name == data["category_name"])
                cat_res = await session.execute(cat_stmt)
                category = cat_res.scalars().first()

                # Resolve SubCategory
                sub_stmt = select(SubCategory).where(SubCategory.name == data["subcategory_name"])
                sub_res = await session.execute(sub_stmt)
                subcategory = sub_res.scalars().first()

                # Resolve or Create Brand
                brand_stmt = select(Brand).where(Brand.name == data["brand_name"])
                brand_res = await session.execute(brand_stmt)
                brand = brand_res.scalars().first()
                if not brand:
                    brand = Brand(name=data["brand_name"])
                    session.add(brand)
                    await session.flush() # Get the ID

                new_listing = Listing(
                    name=data["name"],
                    supplier_id=data["supplier_id"],
                    category_id=category.id if category else "unknown",
                    subcategory_id=subcategory.id if subcategory else None,
                    brand_id=brand.id,
                    price=data["price"],
                    stock_status=data["stock_status"],
                    item_status=data["item_status"],
                    description=data["description"],
                    image_url=data.get("image_url")
                )
                session.add(new_listing)
                print(f"Added listing: {data['name']}")
            else:
                print(f"Listing already exists: {data['name']}")
        
        await session.commit()
        print("Listing seeding completed.")

if __name__ == "__main__":
    asyncio.run(seed_listings())
