# billing/database.py

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import urllib.parse
import asyncio

# ==========================================================
# ✅ DATABASE CONFIGURATION
# ==========================================================
# Encode special characters in password
password = urllib.parse.quote_plus("Shiva@@5405")

# Use asyncmy (or aiomysql if preferred)
DATABASE_URL = f"mysql+asyncmy://root:{password}@localhost:3306/RetailX"

# ==========================================================
# ✅ ENGINE CREATION
# ==========================================================
engine = create_async_engine(
    DATABASE_URL,
    echo=False,            # True = log SQL
    future=True,
    pool_pre_ping=True,    # reconnect automatically if dropped
    poolclass=NullPool     # avoids too many open connections
)

# ==========================================================
# ✅ SESSION FACTORY
# ==========================================================
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# ==========================================================
# ✅ FASTAPI DEPENDENCY
# ==========================================================
async def get_db():
    """Yields a database session for FastAPI routes."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# ==========================================================
# ✅ TEST CONNECTION (optional)
# ==========================================================
if __name__ == "__main__":
    async def test_connection():
        try:
            async with engine.begin() as conn:
                await conn.run_sync(lambda sync_conn: print("✅ Database connected successfully!"))
        except Exception as e:
            print("❌ Database connection failed:", e)

    asyncio.run(test_connection())
