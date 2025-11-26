# app/tests/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime

class BaseTestResult(BaseModel):
    testType: str = Field(..., description="letterMatch | storybook | wordDetective")
    studentId: str
    timeSpent: Optional[float] = Field(..., description="total test duration in seconds")
    metadata: Optional[dict] = None  # device, language, version, etc.

# Letter Match payload (frontend summary style)
class LetterMatchResults(BaseModel):
    correctAnswers: int
    totalQuestions: int
    timeSpent: float

class LetterMatchSubmit(BaseTestResult):
    results: LetterMatchResults
    # optional detailed question data (recommended for analytics)
    questionData: Optional[List[dict]] = None  # each dict: {question, options, selectedOption, isCorrect, timeSpent}

# Storybook payload
class StorybookResults(BaseModel):
    round1Score: int
    round2Score: int
    round3Score: int
    pickedDistractor: Optional[bool] = False
    timeSpent: float
    round4UserOrder: Optional[List[int]] = None
    round5UserOrder: Optional[List[int]] = None
    aiAnalysis: Optional[dict] = None

class StorybookSubmit(BaseTestResult):
    results: StorybookResults
    roundData: Optional[dict] = None

# Word Detective payload
class WordDetectiveResults(BaseModel):
    score: int
    totalQuestions: int
    timeSpent: float

class WordDetectiveSubmit(BaseTestResult):
    results: WordDetectiveResults
    wordPairs: Optional[List[dict]] = None  # optional per-pair details

# Generic union input (allows any of the above shapes)
class TestSubmitUnion(BaseModel):
    testType: str
    studentId: str
    results: dict
    metadata: Optional[dict] = None
    # optional details that frontend may include
    questionData: Optional[List[dict]] = None
    roundData: Optional[dict] = None
    wordPairs: Optional[List[dict]] = None