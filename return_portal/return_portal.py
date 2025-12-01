# return_portal.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from pydantic import BaseModel, validator
from typing import List, Optional
from datetime import datetime
import uuid
import os
import shutil
from enum import Enum

# Router for return portal
return_router = APIRouter(prefix="/returns", tags=["Return Portal"])

# Enums
class ReturnStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    UNDER_REVIEW = "under_review"

class ReturnReason(str, Enum):
    DEFECTIVE = "defective"
    WRONG_ITEM = "wrong_item"
    DAMAGED = "damaged"
    NOT_AS_DESCRIBED = "not_as_described"
    SIZE_ISSUE = "size_issue"
    OTHER = "other"

# Pydantic Models
class ReturnRequestBase(BaseModel):
    customer_name: str
    customer_number: str
    bill_number: str
    reason: ReturnReason
    reason_description: str

class ReturnRequestCreate(ReturnRequestBase):
    pass

class ReturnRequestResponse(ReturnRequestBase):
    id: str
    status: ReturnStatus
    submission_date: datetime
    images: List[str] = []
    analysis_notes: Optional[str] = None
    processed_by: Optional[str] = None
    processed_date: Optional[datetime] = None
    refund_amount: Optional[float] = None
    priority: str

    class Config:
        from_attributes = True

class ProcessReturnRequest(BaseModel):
    action: ReturnStatus
    notes: Optional[str] = None
    refund_amount: Optional[float] = None
    processed_by: str

class ReturnStats(BaseModel):
    total: int
    pending: int
    approved: int
    rejected: int
    under_review: int

# In-memory storage (Replace with database in production)
return_requests_db = []

class ReturnAnalysisService:
    def __init__(self):
        self.auto_approve_reasons = [ReturnReason.WRONG_ITEM, ReturnReason.SIZE_ISSUE]
        self.high_priority_reasons = [ReturnReason.DEFECTIVE, ReturnReason.DAMAGED]
    
    def analyze_return_request(self, request_data: ReturnRequestCreate, has_images: bool) -> dict:
        analysis = {
            "confidence_score": 0,
            "recommended_action": "manual_review",
            "risk_level": "medium",
            "auto_approvable": False,
            "analysis_notes": [],
            "priority": "medium"
        }
        
        # Auto-approval check
        if request_data.reason in self.auto_approve_reasons:
            analysis["auto_approvable"] = True
            analysis["recommended_action"] = "approve"
            analysis["confidence_score"] += 30
        
        # Image evidence check
        if has_images:
            analysis["confidence_score"] += 20
            analysis["analysis_notes"].append("Images provided as evidence")
        else:
            analysis["confidence_score"] -= 10
            analysis["analysis_notes"].append("No images provided - requires manual review")
        
        # Reason description analysis
        analysis["confidence_score"] += self._analyze_reason_description(request_data.reason_description)
        
        # Priority determination
        if request_data.reason in self.high_priority_reasons:
            analysis["priority"] = "high"
        elif request_data.reason in self.auto_approve_reasons:
            analysis["priority"] = "low"
        
        # Risk level calculation
        analysis["risk_level"] = self._calculate_risk_level(analysis["confidence_score"])
        
        return analysis
    
    def _analyze_reason_description(self, description: str) -> int:
        score = 0
        words = description.lower().split()
        
        if len(words) > 10:
            score += 10
        if len(words) > 20:
            score += 10
        
        specific_keywords = ['broken', 'not working', 'damaged', 'wrong', 'defective']
        found_keywords = [word for word in words if word in specific_keywords]
        score += len(found_keywords) * 5
        
        return min(score, 40)
    
    def _calculate_risk_level(self, confidence_score: int) -> str:
        if confidence_score >= 70:
            return "low"
        elif confidence_score >= 40:
            return "medium"
        else:
            return "high"

# Initialize services
analysis_service = ReturnAnalysisService()

# Utility functions
def save_uploaded_images(files: List[UploadFile], request_id: str) -> List[str]:
    """Save uploaded images and return their paths"""
    image_paths = []
    upload_dir = f"uploads/returns/{request_id}"
    
    # Create directory if it doesn't exist
    os.makedirs(upload_dir, exist_ok=True)
    
    for file in files:
        # Generate unique filename
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4().hex}{file_extension}"
        file_path = os.path.join(upload_dir, unique_filename)
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        image_paths.append(file_path)
    
    return image_paths

def generate_request_id() -> str:
    """Generate unique return request ID"""
    return f"RET{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"

def find_return_request(request_id: str):
    """Find return request by ID"""
    for request in return_requests_db:
        if request["id"] == request_id:
            return request
    return None

# API Endpoints
@return_router.post("/submit", response_model=dict)
async def submit_return_request(
    customer_name: str = Form(..., description="Customer full name"),
    customer_number: str = Form(..., description="Customer phone number"),
    bill_number: str = Form(..., description="Bill/receipt number"),
    reason: ReturnReason = Form(..., description="Reason for return"),
    reason_description: str = Form(..., description="Detailed description"),
    images: List[UploadFile] = File(None, description="Product images")
):
    """
    Submit a new return request with product images
    """
    try:
        # Generate unique request ID
        request_id = generate_request_id()
        
        # Save uploaded images
        image_paths = []
        if images:
            image_paths = save_uploaded_images(images, request_id)
        
        # Create return request data
        request_data = ReturnRequestCreate(
            customer_name=customer_name,
            customer_number=customer_number,
            bill_number=bill_number,
            reason=reason,
            reason_description=reason_description
        )
        
        # Analyze the return request
        analysis = analysis_service.analyze_return_request(
            request_data, 
            has_images=len(image_paths) > 0
        )
        
        # Determine initial status
        initial_status = ReturnStatus.PENDING
        analysis_notes = " | ".join(analysis["analysis_notes"])
        
        # Auto-approval logic
        if analysis["auto_approvable"] and analysis["confidence_score"] >= 60:
            initial_status = ReturnStatus.APPROVED
            analysis_notes += " | Auto-approved based on analysis"
        
        # Create return request object
        return_request = {
            "id": request_id,
            "customer_name": customer_name,
            "customer_number": customer_number,
            "bill_number": bill_number,
            "reason": reason,
            "reason_description": reason_description,
            "status": initial_status,
            "submission_date": datetime.now(),
            "images": image_paths,
            "analysis_notes": analysis_notes,
            "processed_by": None,
            "processed_date": None,
            "refund_amount": None,
            "priority": analysis["priority"]
        }
        
        # Store in database (in-memory for demo)
        return_requests_db.append(return_request)
        
        return {
            "success": True,
            "message": f"Return request submitted successfully. Status: {initial_status.value}",
            "request_id": request_id,
            "status": initial_status.value,
            "analysis": analysis
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting return request: {str(e)}")

@return_router.get("/requests", response_model=List[ReturnRequestResponse])
async def get_return_requests(
    status: Optional[ReturnStatus] = None,
    skip: int = 0,
    limit: int = 100
):
    """
    Get all return requests with optional status filtering
    """
    try:
        filtered_requests = return_requests_db
        
        if status:
            filtered_requests = [req for req in return_requests_db if req["status"] == status]
        
        # Apply pagination
        paginated_requests = filtered_requests[skip:skip + limit]
        
        return paginated_requests
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching return requests: {str(e)}")

@return_router.get("/requests/{request_id}", response_model=ReturnRequestResponse)
async def get_return_request(request_id: str):
    """
    Get specific return request by ID
    """
    return_request = find_return_request(request_id)
    
    if not return_request:
        raise HTTPException(status_code=404, detail="Return request not found")
    
    return return_request

@return_router.post("/requests/{request_id}/process", response_model=dict)
async def process_return_request(
    request_id: str,
    process_data: ProcessReturnRequest
):
    """
    Process a return request (approve/reject)
    """
    try:
        return_request = find_return_request(request_id)
        
        if not return_request:
            raise HTTPException(status_code=404, detail="Return request not found")
        
        if return_request["status"] != ReturnStatus.PENDING:
            raise HTTPException(status_code=400, detail="Return request already processed")
        
        # Update return request
        return_request["status"] = process_data.action
        return_request["analysis_notes"] = process_data.notes
        return_request["processed_by"] = process_data.processed_by
        return_request["processed_date"] = datetime.now()
        
        if process_data.refund_amount:
            return_request["refund_amount"] = process_data.refund_amount
        
        return {
            "success": True,
            "message": f"Return request {process_data.action.value} successfully",
            "request_id": request_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing return request: {str(e)}")

@return_router.get("/stats", response_model=ReturnStats)
async def get_return_stats():
    """
    Get return request statistics
    """
    try:
        total = len(return_requests_db)
        pending = len([r for r in return_requests_db if r["status"] == ReturnStatus.PENDING])
        approved = len([r for r in return_requests_db if r["status"] == ReturnStatus.APPROVED])
        rejected = len([r for r in return_requests_db if r["status"] == ReturnStatus.REJECTED])
        under_review = len([r for r in return_requests_db if r["status"] == ReturnStatus.UNDER_REVIEW])
        
        return ReturnStats(
            total=total,
            pending=pending,
            approved=approved,
            rejected=rejected,
            under_review=under_review
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching statistics: {str(e)}")

@return_router.delete("/requests/{request_id}")
async def delete_return_request(request_id: str):
    """
    Delete a return request (for testing/cleanup)
    """
    global return_requests_db
    
    return_requests_db = [req for req in return_requests_db if req["id"] != request_id]
    
    return {"success": True, "message": "Return request deleted successfully"}