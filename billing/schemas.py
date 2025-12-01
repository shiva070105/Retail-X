from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class ProductBase(BaseModel):
    name: str
    barcode: Optional[str] = None
    price: float
    category: Optional[str] = None
    description: Optional[str] = None
    stock: int

class ProductCreate(ProductBase):
    pass

class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class BillingItem(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    unit_price: float
    total_price: float

class BillCreate(BaseModel):
    items: List[BillingItem]
    tax_percentage: float = 0.0
    discount_amount: float = 0.0

class BillResponse(BaseModel):
    id: int
    bill_number: str
    total_amount: float
    tax_amount: float
    discount_amount: float
    final_amount: float
    items: List[Dict[str, Any]]
    created_at: datetime
    
    class Config:
        from_attributes = True

class BillingSessionCreate(BaseModel):
    session_id: str

class BillingSessionResponse(BaseModel):
    id: int
    session_id: str
    items: List[Dict[str, Any]]
    total_amount: float
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class DetectionResponse(BaseModel):
    detected_product: str
    product_details: Dict[str, Any]

class MultiDetectionResponse(BaseModel):
    detected_products: List[str]
    products_details: List[Dict[str, Any]]
    total_items: int
    estimated_total: float