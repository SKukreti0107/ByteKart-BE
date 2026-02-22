import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(DATABASE_URL, echo=True)

async def add_variant_combinations():
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE listing ADD COLUMN variant_combinations JSON;"))
            print("Added variant_combinations col to listing.")
        except Exception as e:
            print(f"Error adding variant_combinations: {e}")

if __name__ == "__main__":
    asyncio.run(add_variant_combinations())
