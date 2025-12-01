# ==========================================================
# return_portal/crud.py
# ==========================================================
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime
from typing import Optional
import uuid
from .database import ReturnRequest

# ==========================================================
# ✅ CREATE RETURN REQUEST
# ==========================================================
async def create_return_request(
    db: AsyncSession,
    customer_name: str,
    customer_number: str,
    bill_number: str,
    reason: str,
    reason_description: str,
    status: str = "pending",
    analysis_notes: Optional[str] = None,
    priority: str = "medium",
):
    request_id = f"RET{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"
    db_return = ReturnRequest(
        request_id=request_id,
        customer_name=customer_name,
        customer_number=customer_number,
        bill_number=bill_number,
        reason=reason,
        reason_description=reason_description,
        status=status,
        analysis_notes=analysis_notes,
        priority=priority,
    )
    db.add(db_return)
    await db.commit()
    await db.refresh(db_return)
    return db_return

# ==========================================================
# ✅ GET ALL RETURN REQUESTS
# ==========================================================
async def get_return_requests(db: AsyncSession, status: Optional[str] = None):
    query = select(ReturnRequest)
    if status:
        query = query.where(ReturnRequest.status == status)
    result = await db.execute(query)
    return result.scalars().all()

# ==========================================================
# ✅ GET RETURN REQUEST BY ID
# ==========================================================
async def get_return_request_by_id(db: AsyncSession, request_id: str):
    result = await db.execute(select(ReturnRequest).where(ReturnRequest.request_id == request_id))
    return result.scalar_one_or_none()

# ==========================================================
# ✅ UPDATE STATUS
# ==========================================================
async def update_return_request_status(
    db: AsyncSession,
    request_id: str,
    status: str,
    processed_by: str,
    analysis_notes: Optional[str] = None,
    refund_amount: Optional[float] = None,
):
    result = await db.execute(select(ReturnRequest).where(ReturnRequest.request_id == request_id))
    return_request = result.scalar_one_or_none()

    if return_request:
        return_request.status = status
        return_request.processed_by = processed_by
        return_request.processed_date = datetime.utcnow()
        if analysis_notes:
            return_request.analysis_notes = analysis_notes
        if refund_amount:
            return_request.refund_amount = refund_amount

        await db.commit()
        await db.refresh(return_request)

    return return_request

# ==========================================================
# ✅ GET STATISTICS
# ==========================================================
async def get_return_stats(db: AsyncSession):
    total = len((await db.execute(select(ReturnRequest))).scalars().all())
    pending = len((await db.execute(select(ReturnRequest).where(ReturnRequest.status == "pending"))).scalars().all())
    approved = len((await db.execute(select(ReturnRequest).where(ReturnRequest.status == "approved"))).scalars().all())
    rejected = len((await db.execute(select(ReturnRequest).where(ReturnRequest.status == "rejected"))).scalars().all())
    under_review = len((await db.execute(select(ReturnRequest).where(ReturnRequest.status == "under_review"))).scalars().all())

    return {
        "total": total,
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
        "under_review": under_review,
    }
