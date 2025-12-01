from pydantic import BaseModel

class UserCreate(BaseModel):
    phone_number: str
    name: str | None = None

class UserResponse(BaseModel):
    id: int
    phone_number: str
    name: str | None
    loyalty_points: int

    class Config:
        from_attributes = True

class OTPRequest(BaseModel):
    phone_number: str

class OTPVerify(BaseModel):
    phone_number: str
    otp_code: str
