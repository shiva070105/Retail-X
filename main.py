# ==========================================================
# main.py — RetailX Backend (with Return Portal + Theft Detection)
# ==========================================================

import threading
from fastapi import FastAPI, Depends, HTTPException, Query, Form
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime
from enum import Enum

# --- Import existing RetailX modules ---
from billing.database import get_db
from billing.crud import get_product_by_barcode
from billing.routes import image_routes, barcode_routes

# --- Return Portal modules ---
from return_portal.database import get_db as get_return_db, create_tables
from return_portal.crud import (
    create_return_request,
    get_return_requests,
    get_return_request_by_id,
    update_return_request_status,
    get_return_stats
)

# --- 🔹 Theft Detection Module ---
from monitoring.theft_detector import TheftDetector

# ==========================================================
# ✅ FASTAPI INITIALIZATION
# ==========================================================
app = FastAPI(title="RetailX API", version="2.0")

# ==========================================================
# ✅ DATABASE TABLE CREATION + THEFT DETECTOR STARTUP
# ==========================================================
@app.on_event("startup")
async def startup_event():
    await create_tables()
    print("✅ Return Portal tables are ready!")

    # 🔹 Start theft detection in background thread
    def run_theft_detector():
        try:
            detector = TheftDetector()  # model, telegram, and dataset paths are defined inside theft_detector.py
            detector.run(source=0)      # 0 = webcam; change to video path if needed
        except Exception as e:
            print(f"❌ Theft detector failed to start: {e}")

    threading.Thread(target=run_theft_detector, daemon=True).start()
    print("🚀 Theft detection system started in background!")


# ==========================================================
# ✅ ENUMS AND RESPONSE MODELS
# ==========================================================
class ReturnStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    UNDER_REVIEW = "under_review"


class ReturnRequestResponse(BaseModel):
    request_id: str
    customer_name: str
    customer_number: str
    bill_number: str
    reason: str
    reason_description: str
    status: str
    submission_date: datetime
    analysis_notes: Optional[str] = None


class ProcessReturnRequest(BaseModel):
    action: str
    notes: Optional[str] = None
    refund_amount: Optional[float] = None
    processed_by: str


class ReturnStats(BaseModel):
    total: int
    pending: int
    approved: int
    rejected: int
    under_review: int


# ==========================================================
# ✅ RETURN PORTAL ENDPOINTS
# ==========================================================
@app.post("/returns/submit", tags=["Return Portal"])
async def submit_return_request(
    customer_name: str = Form(...),
    customer_number: str = Form(...),
    bill_number: str = Form(...),
    reason: str = Form(...),
    reason_description: str = Form(...),
    db: AsyncSession = Depends(get_return_db)
):
    try:
        new_request = await create_return_request(
            db=db,
            customer_name=customer_name,
            customer_number=customer_number,
            bill_number=bill_number,
            reason=reason,
            reason_description=reason_description,
        )
        return {
            "success": True,
            "message": "Return request submitted successfully",
            "request_id": new_request.request_id,
            "status": new_request.status,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting return request: {str(e)}")


@app.get("/returns/requests", response_model=List[ReturnRequestResponse], tags=["Return Portal"])
async def get_all_return_requests(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_return_db)
):
    try:
        requests = await get_return_requests(db, status)
        return requests
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching return requests: {str(e)}")


@app.get("/returns/requests/{request_id}", response_model=ReturnRequestResponse, tags=["Return Portal"])
async def get_return_request_details(request_id: str, db: AsyncSession = Depends(get_return_db)):
    request = await get_return_request_by_id(db, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Return request not found")
    return request


@app.post("/returns/requests/{request_id}/process", tags=["Return Portal"])
async def process_return_request(
    request_id: str,
    process_data: ProcessReturnRequest,
    db: AsyncSession = Depends(get_return_db)
):
    try:
        updated = await update_return_request_status(
            db=db,
            request_id=request_id,
            status=process_data.action,
            processed_by=process_data.processed_by,
            analysis_notes=process_data.notes,
            refund_amount=process_data.refund_amount,
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Return request not found")
        return {
            "success": True,
            "message": f"Return request {process_data.action} successfully",
            "request_id": request_id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating return request: {str(e)}")


@app.get("/returns/stats", response_model=ReturnStats, tags=["Return Portal"])
async def get_return_portal_stats(db: AsyncSession = Depends(get_return_db)):
    try:
        stats = await get_return_stats(db)
        return ReturnStats(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching return stats: {str(e)}")


@app.get("/returns/test", tags=["Return Portal"])
async def test_return_portal(db: AsyncSession = Depends(get_return_db)):
    stats = await get_return_stats(db)
    return {
        "message": "Return portal is working correctly ✅",
        "database": "Connected to MySQL RetailX",
        "tables_created": True,
        "total_requests": stats["total"],
        "endpoints": [
            "POST /returns/submit",
            "GET /returns/requests",
            "GET /returns/requests/{request_id}",
            "POST /returns/requests/{request_id}/process",
            "GET /returns/stats"
        ]
    }


# ==========================================================
# ✅ BARCODE MODULE (Existing)
# ==========================================================
class BarcodeRequest(BaseModel):
    barcode: str


@app.post("/scan-barcode/", tags=["Barcode Detection"])
async def scan_barcode(request: BarcodeRequest, db: AsyncSession = Depends(get_db)):
    barcode_value = request.barcode.strip()
    product = await get_product_by_barcode(db, barcode_value)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product not found for barcode {barcode_value}")
    return {"status": "success", "product": product}


@app.get("/scan-barcode/", tags=["Barcode Detection"])
async def get_barcode_product(
    barcode: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    product = await get_product_by_barcode(db, barcode.strip())
    if not product:
        raise HTTPException(status_code=404, detail=f"Product not found for barcode {barcode}")
    return {"status": "success", "product": product}


@app.get("/products/barcode/{barcode}", tags=["Barcode Detection"])
async def read_product_by_barcode(barcode: str, db: AsyncSession = Depends(get_db)):
    product = await get_product_by_barcode(db, barcode.strip())
    if not product:
        raise HTTPException(status_code=404, detail=f"Product not found for barcode {barcode}")
    return {"status": "success", "product": product}


# ==========================================================
# ✅ THEFT DETECTION ENDPOINT
# ==========================================================
@app.get("/theft/status", tags=["Theft Detection"])
async def theft_status():
    return {
        "status": "active",
        "source": "webcam",
        "alert_method": "Telegram",
        "message": "Theft detection module is running in background 🚨"
    }


# ==========================================================
# ✅ GENERAL APP INFO
# ==========================================================
@app.get("/")
async def root():
    return {"message": "RetailX Backend (with Theft Detection) is running!"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "RetailX API is operational"}


@app.get("/debug-routes")
async def debug_routes():
    routes = [
        {"path": route.path, "methods": list(route.methods)}
        for route in app.routes
    ]
    return {"total_routes": len(routes), "routes": routes}


# ==========================================================
# ✅ INCLUDE OTHER ROUTERS (IMAGE + BARCODE)
# ==========================================================
app.include_router(image_routes.router, prefix="/image", tags=["Image Detection"])
app.include_router(barcode_routes.router, prefix="/barcode", tags=["Barcode Detection"])
