import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(DATABASE_URL, echo=True)

async def drop_item_status():
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE listing DROP COLUMN item_status;"))
            print("Dropped item_status col from listing.")
        except Exception as e:
            print(f"Error dropping item_status: {e}")

if __name__ == "__main__":
    asyncio.run(drop_item_status())
