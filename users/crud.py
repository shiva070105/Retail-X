import random
from sqlalchemy.orm import Session
from . import models, schemas

def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(phone_number=user.phone_number, name=user.name)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user_by_phone(db: Session, phone_number: str):
    return db.query(models.User).filter(models.User.phone_number == phone_number).first()

def generate_otp(db: Session, phone_number: str):
    otp = str(random.randint(1000, 9999))
    db_otp = models.OTP(phone_number=phone_number, otp_code=otp)
    db.add(db_otp)
    db.commit()
    db.refresh(db_otp)
    return otp

def verify_otp(db: Session, phone_number: str, otp_code: str):
    otp_entry = db.query(models.OTP).filter(
        models.OTP.phone_number == phone_number,
        models.OTP.otp_code == otp_code
    ).first()
    return otp_entry is not None
