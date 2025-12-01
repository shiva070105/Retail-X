from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from . import crud, schemas, database

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    db_user = crud.get_user_by_phone(db, user.phone_number)
    if db_user:
        raise HTTPException(status_code=400, detail="Phone number already registered")
    return crud.create_user(db, user)

@router.post("/send-otp")
def send_otp(request: schemas.OTPRequest, db: Session = Depends(database.get_db)):
    otp = crud.generate_otp(db, request.phone_number)
    # TODO: integrate SMS gateway (Twilio/MSG91/etc.)
    return {"message": "OTP sent successfully", "otp": otp}  # ⚠️ Debug only, remove `otp` in production

@router.post("/verify-otp")
def verify_otp(request: schemas.OTPVerify, db: Session = Depends(database.get_db)):
    if crud.verify_otp(db, request.phone_number, request.otp_code):
        return {"message": "OTP verified successfully"}
    raise HTTPException(status_code=400, detail="Invalid OTP")
