import asyncio
import sys
import os

# Add the parent directory to sys.path to import from db and models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import select
from db import async_session_maker
from models import Category, SubCategory

async def seed_subcategories():
    # Define subcategories mapped to their parent category names
    subcategories_data = {
        "Laptops": ["Gaming Laptops", "Ultrabooks", "Business Laptops", "2-in-1 Laptops"],
        "Smartphones": ["Android Phones", "iPhones", "Refurbished Phones"],
        "Tablets": ["iPads", "Android Tablets", "Windows Tablets", "E-Readers"],
        "Accessories": ["Cases & Covers", "Chargers & Cables", "Screen Protectors", "Power Banks"],
        "Monitors": ["Gaming Monitors", "Ultrawide Monitors", "4K Monitors", "Portable Monitors"],
        "Components": ["Processors (CPU)", "Graphics Cards (GPU)", "Motherboards", "RAM", "Power Supplies (PSU)"],
        "Networking": ["Routers", "Switches", "Wi-Fi Extenders", "Network Cards"],
        "Audio": ["Headphones", "Earbuds", "Bluetooth Speakers", "Soundbars"],
        "Wearables": ["Smartwatches", "Fitness Trackers", "VR Headsets"],
        "Gaming": ["Consoles", "Controllers", "Gaming Keyboards", "Gaming Mice"],
        "Storage": ["Internal SSDs", "External Hard Drives", "USB Flash Drives", "NAS"]
    }

    async with async_session_maker() as session:
        for category_name, subcategories in subcategories_data.items():
            # Find the parent category
            statement = select(Category).where(Category.name == category_name)
            result = await session.execute(statement)
            category = result.scalars().first()

            if not category:
                print(f"Warning: Category '{category_name}' not found. Skipping its subcategories.")
                continue

            for subcategory_name in subcategories:
                # Check if subcategory already exists for this category
                sub_statement = select(SubCategory).where(
                    (SubCategory.name == subcategory_name) & 
                    (SubCategory.category_id == category.id)
                )
                sub_result = await session.execute(sub_statement)
                existing_subcategory = sub_result.scalars().first()

                if not existing_subcategory:
                    new_subcategory = SubCategory(name=subcategory_name, category_id=category.id)
                    session.add(new_subcategory)
                    print(f"Added subcategory: {subcategory_name} (under {category_name})")
                else:
                    print(f"Subcategory already exists: {subcategory_name} (under {category_name})")
        
        await session.commit()
        print("Subcategory seeding completed.")

if __name__ == "__main__":
    asyncio.run(seed_subcategories())
