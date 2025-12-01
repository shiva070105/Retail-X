# return_portal/models.py
from .database import Base
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

class ReturnRequest(Base):
    __tablename__ = "return_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(50), unique=True, index=True, nullable=False)
    customer_name = Column(String(100), nullable=False)
    customer_number = Column(String(15), nullable=False)
    bill_number = Column(String(50), nullable=False)
    reason = Column(String(50), nullable=False)
    reason_description = Column(Text, nullable=False)
    status = Column(String(20), default="pending")
    submission_date = Column(DateTime, default=datetime.utcnow)
    analysis_notes = Column(Text)
    processed_by = Column(String(100))
    processed_date = Column(DateTime)
    refund_amount = Column(Float)
    priority = Column(String(10), default="medium")
    
    # Relationship with images
    images = relationship("ReturnImage", back_populates="return_request")

class ReturnImage(Base):
    __tablename__ = "return_images"
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(50), ForeignKey("return_requests.request_id"), nullable=False)
    image_path = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship with return request
    return_request = relationship("ReturnRequest", back_populates="images")