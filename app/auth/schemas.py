# app/auth/schemas.py
from pydantic import BaseModel, EmailStr, Field, validator
from typing import List, Optional

# --- Registration payload shape exactly as frontend sends it ---
class RegistrationData(BaseModel):
    parentName: str
    relationship: str
    email: EmailStr
    mobile: Optional[str] = None
    preferredLanguage: str

    childName: str
    childAge: str
    childGrade: str
    primaryLanguage: str
    languagesCanRead: List[str]

    strugglingWithReading: str
    letterMixups: str
    feelingAboutReading: str
    teacherMentioned: str
    difficultySpelling: str
    prefersListening: str

    problemsSince: str
    problemAreas: List[str]
    additionalInfo: Optional[str] = None

    consentAnalysis: bool
    password: str

    @validator("consentAnalysis")
    def consent_must_be_true(cls, v):
        if v is not True:
            raise ValueError("consentAnalysis must be true to submit registration")
        return v

class RegisterResponse(BaseModel):
    success: bool
    message: str
    data: dict

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    success: bool
    message: str
    data: dict

class MeResponse(BaseModel):
    data: dict