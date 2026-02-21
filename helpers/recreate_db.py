import asyncio
from models import *
from db import engine
from sqlmodel import SQLModel

async def recreate():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)

if __name__ == "__main__":
    asyncio.run(recreate())
