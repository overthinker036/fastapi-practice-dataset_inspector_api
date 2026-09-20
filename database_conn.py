from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
import asyncio
from sqlalchemy import text

DB_URL = "sqlite+aiosqlite:///./mydb.db"

engine = create_async_engine(DB_URL)

AsyncSessionLocal = async_sessionmaker(autoflush=False, autocommit=False, bind=engine)

# async def check():
#     async with engine.connect() as conn:
#         result = await conn.execute(text("SELECT 1"))
#         print("Connected! Result:", result.scalar())

# asyncio.run(check())