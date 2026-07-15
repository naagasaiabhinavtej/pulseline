from pydantic import BaseModel
from typing import Optional

class SessionResponse(BaseModel):
    session_id:int
    health_name:str
    clinic_name:str
    message:str

    class Config:
        form_attributes = True

class patientRegister(BaseModel):
    name: str
    date_of_birth: str
    gender: str
    blood_group: str
    height: float
    weight: float
    emergency_contact: str
    allergies: str | None = None               #modern way but you can use optional[str] = None
    medical_data: str | None = None
    password: str
