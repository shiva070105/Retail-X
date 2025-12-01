from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text
from typing import List, Optional, Dict, Any
import json
from datetime import datetime
import uuid

from .models import Product, Bill, BillingSession
from .schemas import ProductCreate, BillCreate, BillingSessionCreate

# Product CRUD operations
async def get_product_by_name(db: AsyncSession, product_name: str):
    """Get product by name using your exact column names"""
    try:
        # Use raw SQL with your exact column names
        query = text("""
            SELECT ProductID, ProductName, Barcode, Category, Brand, Price, Weight, StockQuantity 
            FROM products 
            WHERE ProductName = :name 
            LIMIT 1
        """)
        result = await db.execute(query, {"name": product_name})
        row = result.fetchone()
        
        if row:
            # Convert row to dictionary
            if hasattr(row, '_mapping'):
                row_dict = dict(row._mapping)
            else:
                row_dict = dict(row)
            
            # Create a Product-like object with your exact column names
            class DynamicProduct:
                def __init__(self, data):
                    self.id = data.get('ProductID')
                    self.name = data.get('ProductName') or product_name
                    self.barcode = data.get('Barcode')
                    self.category = data.get('Category', 'Unknown')
                    self.brand = data.get('Brand', 'Unknown')
                    self.price = float(data.get('Price', 0.0))
                    self.weight = data.get('Weight', 'N/A')
                    self.stock = data.get('StockQuantity', 0)
            
            return DynamicProduct(row_dict)
        else:
            # Try case-insensitive search
            query_ci = text("""
                SELECT ProductID, ProductName, Barcode, Category, Brand, Price, Weight, StockQuantity 
                FROM products 
                WHERE LOWER(ProductName) = LOWER(:name) 
                LIMIT 1
            """)
            result_ci = await db.execute(query_ci, {"name": product_name})
            row_ci = result_ci.fetchone()
            
            if row_ci:
                if hasattr(row_ci, '_mapping'):
                    row_dict = dict(row_ci._mapping)
                else:
                    row_dict = dict(row_ci)
                
                class DynamicProduct:
                    def __init__(self, data):
                        self.id = data.get('ProductID')
                        self.name = data.get('ProductName') or product_name
                        self.barcode = data.get('Barcode')
                        self.category = data.get('Category', 'Unknown')
                        self.brand = data.get('Brand', 'Unknown')
                        self.price = float(data.get('Price', 0.0))
                        self.weight = data.get('Weight', 'N/A')
                        self.stock = data.get('StockQuantity', 0)
                
                return DynamicProduct(row_dict)
                    
        return None
        
    except Exception as e:
        print(f"Error in get_product_by_name for '{product_name}': {e}")
        return None

async def get_product_by_barcode(db: AsyncSession, barcode: str):
    """Get product by barcode using your exact column names"""
    try:
        # Use raw SQL with your exact column names
        query = text("""
            SELECT ProductID, ProductName, Barcode, Category, Brand, Price, Weight, StockQuantity 
            FROM products 
            WHERE Barcode = :barcode 
            LIMIT 1
        """)
        result = await db.execute(query, {"barcode": barcode})
        row = result.fetchone()
        
        if row:
            # Convert row to dictionary
            if hasattr(row, '_mapping'):
                row_dict = dict(row._mapping)
            else:
                row_dict = dict(row)
            
            # Create a Product-like object with your exact column names
            class DynamicProduct:
                def __init__(self, data):
                    self.id = data.get('ProductID')
                    self.name = data.get('ProductName', 'Unknown Product')
                    self.barcode = data.get('Barcode') or barcode
                    self.category = data.get('Category', 'Unknown')
                    self.brand = data.get('Brand', 'Unknown')
                    self.price = float(data.get('Price', 0.0))
                    self.weight = data.get('Weight', 'N/A')
                    self.stock = data.get('StockQuantity', 0)
            
            return DynamicProduct(row_dict)
                    
        return None
        
    except Exception as e:
        print(f"Error in get_product_by_barcode for barcode '{barcode}': {e}")
        return None

async def get_product_by_id(db: AsyncSession, product_id: int):
    try:
        query = text("""
            SELECT ProductID, ProductName, Barcode, Category, Brand, Price, Weight, StockQuantity 
            FROM products 
            WHERE ProductID = :id 
            LIMIT 1
        """)
        result = await db.execute(query, {"id": product_id})
        return result.scalar_one_or_none()
    except Exception as e:
        print(f"Error in get_product_by_id: {e}")
        return None

async def get_all_products(db: AsyncSession, skip: int = 0, limit: int = 100):
    try:
        query = text("""
            SELECT ProductID, ProductName, Barcode, Category, Brand, Price, Weight, StockQuantity 
            FROM products 
            LIMIT :limit OFFSET :offset
        """)
        result = await db.execute(query, {"limit": limit, "offset": skip})
        return result.fetchall()
    except Exception as e:
        print(f"Error in get_all_products: {e}")
        return []

async def create_product(db: AsyncSession, product: ProductCreate):
    try:
        # Use your exact column names for insertion
        query = text("""
            INSERT INTO products (ProductName, Barcode, Category, Brand, Price, Weight, StockQuantity)
            VALUES (:name, :barcode, :category, :brand, :price, :weight, :stock)
        """)
        await db.execute(query, {
            "name": product.name,
            "barcode": product.barcode,
            "category": product.category,
            "brand": product.brand or "Unknown",
            "price": product.price,
            "weight": product.weight or "N/A",
            "stock": product.stock
        })
        await db.commit()
        return {"message": "Product created successfully"}
    except Exception as e:
        await db.rollback()
        print(f"Error in create_product: {e}")
        raise e

# Bill CRUD operations
async def create_bill(db: AsyncSession, bill: BillCreate):
    # Calculate amounts
    total_amount = sum(item.total_price for item in bill.items)
    tax_amount = total_amount * (bill.tax_percentage / 100)
    final_amount = total_amount + tax_amount - bill.discount_amount
    
    # Generate bill number
    bill_number = f"BILL-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    
    # Convert items to JSON-serializable format
    items_data = [item.dict() for item in bill.items]
    
    db_bill = Bill(
        bill_number=bill_number,
        total_amount=total_amount,
        tax_amount=tax_amount,
        discount_amount=bill.discount_amount,
        final_amount=final_amount,
        items=items_data
    )
    
    db.add(db_bill)
    await db.commit()
    await db.refresh(db_bill)
    return db_bill

async def get_bill_by_id(db: AsyncSession, bill_id: int):
    result = await db.execute(select(Bill).filter(Bill.id == bill_id))
    return result.scalar_one_or_none()

async def get_all_bills(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(Bill).order_by(Bill.created_at.desc()).offset(skip).limit(limit))
    return result.scalars().all()

# Billing Session CRUD operations
async def create_billing_session(db: AsyncSession, session_data: BillingSessionCreate):
    db_session = BillingSession(
        session_id=session_data.session_id,
        items=[],
        total_amount=0.0
    )
    db.add(db_session)
    await db.commit()
    await db.refresh(db_session)
    return db_session

async def get_billing_session(db: AsyncSession, session_id: str):
    result = await db.execute(select(BillingSession).filter(BillingSession.session_id == session_id))
    return result.scalar_one_or_none()

async def update_billing_session(db: AsyncSession, session_id: str, items: List[dict], total_amount: float):
    result = await db.execute(select(BillingSession).filter(BillingSession.session_id == session_id))
    session = result.scalar_one_or_none()
    
    if session:
        session.items = items
        session.total_amount = total_amount
        session.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(session)
    
    return session

async def close_billing_session(db: AsyncSession, session_id: str):
    result = await db.execute(select(BillingSession).filter(BillingSession.session_id == session_id))
    session = result.scalar_one_or_none()
    
    if session:
        session.is_active = 0
        await db.commit()
    
    return session