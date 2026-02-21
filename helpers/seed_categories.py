import asyncio
import sys
import os

# Add the parent directory to sys.path to import from db and models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import select
from db import async_session_maker
from models import Category

async def seed_categories():
    categories_to_seed = [
        "Laptops",
        "Smartphones",
        "Tablets",
        "Accessories",
        "Monitors",
        "Components",
        "Networking",
        "Audio",
        "Wearables",
        "Gaming",
        "Storage"
    ]

    async with async_session_maker() as session:
        for category_name in categories_to_seed:
            # Check if category already exists
            statement = select(Category).where(Category.name == category_name)
            result = await session.execute(statement)
            existing_category = result.scalars().first()

            if not existing_category:
                new_category = Category(name=category_name)
                session.add(new_category)
                print(f"Added category: {category_name}")
            else:
                print(f"Category already exists: {category_name}")
        
        await session.commit()
        print("Seeding completed.")

if __name__ == "__main__":
    asyncio.run(seed_categories())
