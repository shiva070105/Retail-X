from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True)
    barcode = Column(String(100), unique=True, index=True)
    price = Column(Float)
    category = Column(String(100))
    description = Column(Text)
    stock = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

class Bill(Base):
    __tablename__ = "bills"
    
    id = Column(Integer, primary_key=True, index=True)
    bill_number = Column(String(100), unique=True, index=True)
    total_amount = Column(Float)
    tax_amount = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    final_amount = Column(Float)
    items = Column(JSON)  # Store as JSON for flexibility
    created_at = Column(DateTime, default=datetime.utcnow)

class BillingSession(Base):
    __tablename__ = "billing_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, index=True)
    items = Column(JSON)  # Current cart items
    total_amount = Column(Float, default=0.0)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)