from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional
import re
from datetime import date, datetime
class SessionResponse(BaseModel):
    session_id:int
    health_name:str
    clinic_name:str
    message:str

    class Config:
        form_attributes = True

class patientRegister(BaseModel):
    name: str
    date_of_birth: date
    gender: str
    blood_group: str
    height: float = Field(gt=0)
    weight: float = Field(gt=0)
    emergency_contact: str
    allergies: str | None = None               #modern way but you can use optional[str] = None
    medical_data: str | None = None
    password: str
    @field_validator("person")
    @classmethod
    def validate_person(cls, value):
        if value != "patient":
            raise ValueError("Invalid user type")
        return value
    @field_validator("gender")
    @classmethod
    def validate_gender(cls, value):
        allowed = {"Male", "Female", "Other"}
        if value not in allowed:
            raise ValueError("Invalid Gender")
        return value
    @field_validator("blood_group")     #refers to value of this type 
    @classmethod                   #refers to this class because of these both you get values down
    def validate_bloodGroup(cls, value):
        allowed = {
            "A+", "A-", "B+", "B-",
            "AB+", "AB-", "O+", "O-"
        }
        if value not in allowed:
            raise ValueError("Invalid blood group")
        return value
    @field_validator("emergency_contact")
    @classmethod
    def validate_emergencyContact(cls, value):
        if not re.fullmatch(r"[6-9]\d{9}", value):
            raise ValueError("Invalid contact")
        return value
    @field_validator("password")
    @classmethod
    def validate_password(cls, value):
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters")

        if len(value) > 32:
            raise ValueError("Password can have at most 32 characters")

        if not re.search(r"[A-Z]", value):
            raise ValueError("Password must contain at least one uppercase letter")

        if not re.search(r"\d", value):
            raise ValueError("Password must contain at least one number")

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", value):
            raise ValueError("Password must contain at least one symbol")

        return value



class doctorRegister(BaseModel):
    person: str
    name: str
    specialisation: str
    contact: str
    assigned_clinic_id: int
    password: str

    @field_validator("person")
    @classmethod
    def validate_person(cls, value):
        if value != "doctor":
            raise ValueError("Invalid user type")
        return value


    @field_validator("specialisation")
    @classmethod
    def validate_specialisation(cls, value):
        allowed = {
            "General_Medicine",
            "Ophthalmology",
            "Otolaryngology",
            "Cardiology",
            "Orthopedics",
            "Neurology",
            "Gastroenterology",
            "Dermatology",
            "OB-GYN",
            "Pediatrics",
            "Psychiatry",
            "Urology"
        }

        if value not in allowed:
            raise ValueError("Invalid specialization")

        return value


    @field_validator("contact")
    @classmethod
    def validate_contact(cls, value):
        if not re.fullmatch(r"\d{10}", value):
            raise ValueError("Contact number must be exactly 10 digits")

        return value


    @field_validator("assigned_clinic_id")
    @classmethod
    def validate_clinic_id(cls, value):
        if value <= 0:
            raise ValueError("Invalid clinic ID")

        return value


    @field_validator("password")
    @classmethod
    def validate_password(cls, value):

        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters")

        if len(value) > 32:
            raise ValueError("Password can have maximum 32 characters")

        if not re.search(r"[A-Z]", value):
            raise ValueError("Password must contain one uppercase letter")

        if not re.search(r"\d", value):
            raise ValueError("Password must contain one number")

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", value):
            raise ValueError("Password must contain one symbol")

        return value
class LoginRequest(BaseModel):
    person=str,
    id=int = Field(gt=0),
    password:str


    @field_validator("person")
    @classmethod
    def validate_person(cls, value):
        allowed = {"doctor", "patient"}
        if value not in allowed:
            raise ValueError("Invalid person")
        return value
    

    @field_validator
    @classmethod
    def validate_password(cls, value):

        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters")

        if len(value) > 32:
            raise ValueError("Password can have maximum 32 characters")

        if not re.search(r"[A-Z]", value):
            raise ValueError("Password must contain one uppercase letter")

        if not re.search(r"\d", value):
            raise ValueError("Password must contain one number")

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", value):
            raise ValueError("Password must contain one symbol")

        return value



class MakeSessionRequest(BaseModel):
    healthId: int = Field(gt=0)
    clinicId: int = Field(gt=0)
    doctorId: int = Field(gt=0)
    department: str

    @field_validator("department")
    @classmethod
    def validate_deparment(cls, value):
        allowed = {
            "General_Medicine",
            "Ophthalmology",
            "Otolaryngology",
            "Cardiology",
            "Orthopedics",
            "Neurology",
            "Gastroenterology",
            "Dermatology",
            "OB-GYN",
            "Pediatrics",
            "Psychiatry",
            "Urology"
        }
        if value not in allowed:
                raise ValueError("Invalid department")
        return value

class Attachment(BaseModel):
    name: str
    type: str

class NewMessage(BaseModel):
    type: str
    tempId: str
    sessionId: int
    timestamp: datetime
    sender_id: int
    text: str = ""
    files: list[Attachment] = []

    @model_validator(mode="after")             #so that after NewMessage validation this runs 
    def validate_message(self):
        if self.text.strip() == "" and len(self.files) == 0:
            raise ValueError(
                "Message must contain text or at least one file."
            )
        return self
    

class Notes(BaseModel):
    sessionId:int = Field(gt=0)
    notes:str = Field(le=5000)
