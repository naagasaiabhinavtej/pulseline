from pydantic import BaseModel
from typing import Optional

class SessionResponse(BaseModel):
    session_id:int
    health_name:str
    clinic_name:str
    message:str

    class Config:
        form_attributes = True
