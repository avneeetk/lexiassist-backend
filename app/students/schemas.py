# app/students/schemas.py
from pydantic import BaseModel
from typing import List, Optional

class StudentCreate(BaseModel):
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
    additionalInfo: Optional[str] = ""

    consentAnalysis: bool

class StudentUpdate(BaseModel):
    # All fields optional for update
    childName: Optional[str]
    childAge: Optional[str]
    childGrade: Optional[str]
    primaryLanguage: Optional[str]
    languagesCanRead: Optional[List[str]]

    strugglingWithReading: Optional[str]
    letterMixups: Optional[str]
    feelingAboutReading: Optional[str]
    teacherMentioned: Optional[str]
    difficultySpelling: Optional[str]
    prefersListening: Optional[str]

    problemsSince: Optional[str]
    problemAreas: Optional[List[str]]
    additionalInfo: Optional[str]