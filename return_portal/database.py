# return_portal/database.py

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from datetime import datetime
import urllib

# ==========================================================
# ✅ DATABASE CONFIGURATION
# ==========================================================
password = urllib.parse.quote_plus("Shiva@@5405")
DATABASE_URL = f"mysql+asyncmy://root:{password}@localhost:3306/RetailX"

# ✅ Disable SQL logs (echo=False)
engine = create_async_engine(DATABASE_URL, echo=False, future=True)

# ✅ Create async session maker
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# ✅ Base model
Base = declarative_base()

# ==========================================================
# ✅ TABLE DEFINITIONS
# ==========================================================
class ReturnRequest(Base):
    __tablename__ = "return_products"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(50), unique=True, index=True, nullable=False)
    customer_name = Column(String(100), nullable=False)
    customer_number = Column(String(15), nullable=False)
    bill_number = Column(String(50), nullable=False)
    reason = Column(String(50), nullable=False)
    reason_description = Column(Text, nullable=False)
    status = Column(String(20), default="pending")
    submission_date = Column(DateTime, default=datetime.utcnow)
    processed_by = Column(String(100))
    processed_date = Column(DateTime)
    refund_amount = Column(Float, default=0.0)
    analysis_notes = Column(Text)
    priority = Column(String(10), default="medium")

# ==========================================================
# ✅ SESSION HANDLER
# ==========================================================
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# ==========================================================
# ✅ CREATE TABLES
# ==========================================================
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Return Portal tables created successfully in RetailX!")
