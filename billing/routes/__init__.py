from fastapi import APIRouter
from .image_routes import router as image_router
from .barcode_routes import router as barcode_router

# Create main router
router = APIRouter(prefix="/api/billing", tags=["Billing"])

# Include sub-routers
router.include_router(image_router)
router.include_router(barcode_router)