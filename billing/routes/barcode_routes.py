from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from billing.database import get_db
from billing.crud import get_product_by_barcode

router = APIRouter(prefix="/barcode", tags=["Barcode Detection"])

@router.get("/scan/{barcode}")
async def scan_barcode_path(barcode: str, db: AsyncSession = Depends(get_db)):
    """
    Fetch product details from DB using a barcode from URL path.
    """
    product = await get_product_by_barcode(db, barcode)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product with barcode '{barcode}' not found")

    return {
        "barcode": barcode,
        "product_details": {
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "category": product.category,
            "stock": product.stock,
        },
    }

@router.get("/scan_live")
async def scan_barcode_live(
    barcode: str = Query(..., description="Barcode number to search"),
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch product details from DB using a barcode from query parameter.
    """
    product = await get_product_by_barcode(db, barcode)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product with barcode '{barcode}' not found")

    return {
        "message": "Product found successfully",
        "barcode": barcode,
        "product": {
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "category": product.category,
            "stock": product.stock,
            "barcode": getattr(product, 'barcode', barcode)
        },
        "status": "success"
    }

@router.get("/debug/products")
async def debug_all_products(db: AsyncSession = Depends(get_db)):
    """Get all products with their barcodes for debugging"""
    try:
        from sqlalchemy import text
        
        query = text("""
            SELECT ProductID, ProductName, Barcode, Category, Brand, Price, Weight, StockQuantity 
            FROM products 
            LIMIT 50
        """)
        result = await db.execute(query)
        products = result.fetchall()
        
        product_list = []
        for product in products:
            if hasattr(product, '_mapping'):
                product_dict = dict(product._mapping)
            else:
                product_dict = dict(product)
            
            product_list.append({
                "product_id": product_dict.get('ProductID'),
                "product_name": product_dict.get('ProductName'),
                "barcode": product_dict.get('Barcode'),
                "category": product_dict.get('Category'),
                "brand": product_dict.get('Brand'),
                "price": product_dict.get('Price'),
                "weight": product_dict.get('Weight'),
                "stock": product_dict.get('StockQuantity')
            })
        
        return {
            "total_products": len(product_list),
            "products": product_list
        }
        
    except Exception as e:
        return {"error": str(e)}

@router.get("/health")
async def barcode_health():
    """Health check for barcode service"""
    return {
        "status": "healthy",
        "service": "barcode_detection",
        "endpoints": [
            "GET /barcode/scan/{barcode} - Barcode from URL path",
            "GET /barcode/scan_live?barcode=123 - Barcode from query parameter",
            "GET /barcode/debug/products - List all products"
        ]
    }