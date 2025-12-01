# return_portal/routes.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime
import uuid
import os
import shutil

from .database import get_db
from .crud import (
    create_return_request, 
    get_return_requests, 
    get_return_request_by_id,
    update_return_request_status,
    get_return_stats,
    create_return_image,
    get_return_images
)

router = APIRouter(prefix="/returns", tags=["Return Portal"])

# Analysis Service
class ReturnAnalysisService:
    def analyze_return_request(self, reason: str, has_images: bool, reason_description: str) -> dict:
        analysis = {
            "confidence_score": 0, 
            "auto_approvable": False, 
            "priority": "medium",
            "analysis_notes": []
        }
        
        if reason in ["wrong_item", "size_issue"]:
            analysis["auto_approvable"] = True
            analysis["confidence_score"] += 30
            analysis["analysis_notes"].append("Eligible for auto-approval")
        
        if has_images:
            analysis["confidence_score"] += 20
            analysis["analysis_notes"].append("Images provided as evidence")
        else:
            analysis["confidence_score"] -= 10
            analysis["analysis_notes"].append("No images provided")
        
        if len(reason_description.split()) > 15:
            analysis["confidence_score"] += 10
            analysis["analysis_notes"].append("Detailed description provided")
        
        if reason in ["defective", "damaged"]:
            analysis["priority"] = "high"
        
        return analysis

analysis_service = ReturnAnalysisService()

def save_uploaded_images(files: List[UploadFile], request_id: str) -> List[str]:
    """Save uploaded images and return their paths"""
    image_paths = []
    upload_dir = f"uploads/returns/{request_id}"
    
    os.makedirs(upload_dir, exist_ok=True)
    
    for file in files:
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4().hex}{file_extension}"
        file_path = os.path.join(upload_dir, unique_filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        image_paths.append(file_path)
    
    return image_paths

@router.post("/submit")
async def submit_return_request(
    customer_name: str = Form(...),
    customer_number: str = Form(...),
    bill_number: str = Form(...),
    reason: str = Form(...),
    reason_description: str = Form(...),
    images: List[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db)
):
    try:
        # Save uploaded images
        image_paths = []
        request_id = f"RET{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"
        
        if images:
            image_paths = save_uploaded_images(images, request_id)
        
        # Analyze the return request
        analysis = analysis_service.analyze_return_request(
            reason, 
            len(image_paths) > 0,
            reason_description
        )
        
        # Determine initial status
        initial_status = "pending"
        analysis_notes = " | ".join(analysis["analysis_notes"])
        
        if analysis["auto_approvable"] and analysis["confidence_score"] >= 50:
            initial_status = "approved"
            analysis_notes += " | Auto-approved"
        
        # Create in database
        return_request = await create_return_request(
            db=db,
            customer_name=customer_name,
            customer_number=customer_number,
            bill_number=bill_number,
            reason=reason,
            reason_description=reason_description,
            status=initial_status,
            analysis_notes=analysis_notes,
            priority=analysis["priority"]
        )
        
        # Save images to database
        for image_path in image_paths:
            await create_return_image(db, return_request.request_id, image_path)
        
        return {
            "success": True,
            "message": f"Return request submitted successfully. Status: {initial_status}",
            "request_id": return_request.request_id,
            "status": initial_status
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting return request: {str(e)}")

@router.get("/requests")
async def get_return_requests(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    try:
        requests = await get_return_requests(db, status, skip, limit)
        return requests
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching return requests: {str(e)}")

@router.get("/requests/{request_id}")
async def get_return_request(request_id: str, db: AsyncSession = Depends(get_db)):
    return_request = await get_return_request_by_id(db, request_id)
    
    if not return_request:
        raise HTTPException(status_code=404, detail="Return request not found")
    
    # Get images for this request
    images = await get_return_images(db, request_id)
    return_request.images = images
    
    return return_request

@router.post("/requests/{request_id}/process")
async def process_return_request(
    request_id: str,
    action: str,
    notes: Optional[str] = None,
    refund_amount: Optional[float] = None,
    processed_by: str = "admin",
    db: AsyncSession = Depends(get_db)
):
    try:
        return_request = await update_return_request_status(
            db=db,
            request_id=request_id,
            status=action,
            processed_by=processed_by,
            analysis_notes=notes,
            refund_amount=refund_amount
        )
        
        if not return_request:
            raise HTTPException(status_code=404, detail="Return request not found")
        
        return {
            "success": True,
            "message": f"Return request {action} successfully",
            "request_id": request_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing return request: {str(e)}")

@router.get("/stats")
async def get_return_stats(db: AsyncSession = Depends(get_db)):
    try:
        stats = await get_return_stats(db)
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching statistics: {str(e)}")

@router.get("/test")
async def test_return_portal():
    return {"message": "Return portal is working!"}