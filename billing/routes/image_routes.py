import io
import cv2
import numpy as np
from fastapi import APIRouter, UploadFile, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from ultralytics import YOLO
from typing import List
from collections import Counter

from billing.database import get_db
from billing.crud import get_product_by_name

router = APIRouter(tags=["Image Detection"])

# Load YOLO model with error handling
try:
    model = YOLO(r"D:\RetailX\backend\models\product_detection\weights\best.pt")
    MODEL_LOADED = True
    print("✅ YOLO model loaded successfully!")
except Exception as e:
    print(f"❌ Error loading YOLO model: {e}")
    model = None
    MODEL_LOADED = False

# Simple detection functions
def detect_objects(model: YOLO, image: np.ndarray, confidence_threshold: float = 0.5) -> List[str]:
    """Detect objects in image using YOLO model"""
    try:
        if not MODEL_LOADED:
            return ["test_product"]
            
        results = model(image, conf=confidence_threshold)
        detected_names = []
        
        for result in results:
            if result.boxes is not None:
                for box in result.boxes:
                    class_id = int(box.cls.item())
                    class_name = model.names[class_id]
                    detected_names.append(class_name)
        
        return detected_names
        
    except Exception as e:
        print(f"❌ Detection error: {e}")
        return []

# ==========================================================
# ✅ Single Product Detection with Database
# ==========================================================
@router.post("/detect_product")
async def detect_product(file: UploadFile, db: AsyncSession = Depends(get_db)):
    """Detect products from uploaded image and get billing details from database"""
    try:
        # Check if model is loaded
        if not MODEL_LOADED:
            raise HTTPException(status_code=500, detail="YOLO model not loaded")
        
        # Validate file
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")

        # Read and decode image
        image_bytes = await file.read()
        if len(image_bytes) == 0:
            raise HTTPException(status_code=400, detail="Empty file")

        np_image = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(np_image, cv2.IMREAD_COLOR)

        if frame is None:
            raise HTTPException(status_code=400, detail="Could not decode image")

        print(f"📸 Image decoded: {frame.shape}")

        # Run detection
        detected_names = detect_objects(model, frame)
        print(f"🔍 Detected products: {detected_names}")

        if not detected_names:
            return {
                "message": "No products detected",
                "detected_products": [],
                "count": 0,
                "status": "success"
            }

        # Get product details from database for each detected product
        products_with_details = []
        products_not_found = []
        
        for product_name in detected_names:
            product = await get_product_by_name(db, product_name)
            if product:
                # Return only the fields needed for billing
                product_details = {
                    "product_id": getattr(product, 'id', None),
                    "product_name": getattr(product, 'name', product_name),
                    "category": getattr(product, 'category', 'Unknown'),
                    "price": float(getattr(product, 'price', 0.0)),
                    "weight": getattr(product, 'weight', 'N/A'),
                    "barcode": getattr(product, 'barcode', ''),
                    "brand": getattr(product, 'brand', 'Unknown'),
                    "stock": getattr(product, 'stock', 0)
                }
                products_with_details.append(product_details)
            else:
                products_not_found.append(product_name)

        # Calculate billing summary
        total_value = sum(product['price'] for product in products_with_details)
        item_count = len(products_with_details)

        return {
            "message": "Detection successful",
            "detected_products": detected_names,
            "billing_products": products_with_details,  # Products with billing details
            "products_not_found": products_not_found,
            "billing_summary": {
                "total_items": item_count,
                "total_value": total_value,
                "items_found": len(products_with_details),
                "items_not_found": len(products_not_found)
            },
            "status": "success"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Unexpected error in detect_product: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# ==========================================================
# ✅ Test Database Connection
# ==========================================================
@router.get("/test-db")
async def test_database(db: AsyncSession = Depends(get_db)):
    """Test database connection and get sample products"""
    try:
        # Get sample products to verify connection
        query = text("""
            SELECT ProductID, ProductName, Category, Brand, Price, Weight, StockQuantity 
            FROM products 
            LIMIT 5
        """)
        result = await db.execute(query)
        sample_products = result.fetchall()
        
        sample_data = []
        for product in sample_products:
            if hasattr(product, '_mapping'):
                product_dict = dict(product._mapping)
            else:
                product_dict = dict(product)
            sample_data.append({
                "product_id": product_dict.get('ProductID'),
                "name": product_dict.get('ProductName'),
                "category": product_dict.get('Category'),
                "brand": product_dict.get('Brand'),
                "price": product_dict.get('Price'),
                "weight": product_dict.get('Weight'),
                "stock": product_dict.get('StockQuantity')
            })
        
        return {
            "database_status": "connected",
            "sample_products": sample_data,
            "total_products_sample": len(sample_data)
        }
        
    except Exception as e:
        return {
            "database_status": "error",
            "error": str(e)
        }

# ==========================================================
# ✅ Health Check
# ==========================================================
@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check for image detection and database"""
    db_status = "unknown"
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy" if MODEL_LOADED else "degraded",
        "model_loaded": MODEL_LOADED,
        "database": db_status,
        "service": "image_detection"
    }