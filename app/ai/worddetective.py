# app/ai/worddetective.py
import os
import json
import re
import statistics
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/api/worddetective", tags=["worddetective"])

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

# ----------------- Models ------------------
class GenerateRequest(BaseModel):
    age: int
    language: Optional[str] = "english"
    difficulties: Optional[List[str]] = []
    preferredLanguage: Optional[str] = "english"

class WordPair(BaseModel):
    correct: str
    wrong: str

class GenerateResponse(BaseModel):
    wordPairs: List[WordPair]

class AttemptEntry(BaseModel):
    questionIndex: int
    presentedPair: Dict[str, str]
    chosenWord: Optional[str]
    chosenWasCorrect: Optional[bool]
    responseTimeSec: Optional[float] = None

class AnalyzeRequest(BaseModel):
    registrationInfo: Optional[GenerateRequest]
    attempts: List[AttemptEntry]
    totalTimeSec: float
    sessionId: Optional[str] = None   # added for backend analysis linking

class PerQuestion(BaseModel):
    questionIndex: int
    correct: str
    chosen: Optional[str]
    wasCorrect: bool
    responseTimeSec: Optional[float] = None

class AnalyzeResponse(BaseModel):
    score: int
    totalQuestions: int
    accuracy: float
    commonMistakes: Dict[str, int]
    perQuestion: Optional[List[PerQuestion]] = None
    risk: Optional[str] = None
    analysisText: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None

# ----------------- Helper Functions ------------------

def simple_mistake_type(correct: str, wrong: str) -> str:
    if not correct or not wrong:
        return "other"
    if correct.lower().replace(" ", "") == wrong.lower().replace(" ", ""):
        return "case/spacing"
    for i in range(len(wrong) - 1):
        if i < len(correct) - 1 and wrong[i + 1] == correct[i] and wrong[i] == correct[i + 1]:
            return "transposition"
    if len(wrong) < len(correct):
        return "missing_letter"
    if len(wrong) > len(correct):
        return "extra_letter"
    if ("ei" in correct.lower() or "ie" in correct.lower()) and ("ei" in wrong.lower() or "ie" in wrong.lower()):
        return "ei/ie_confusion"
    return "other"

def build_generate_prompt(age: int, language: str, difficulties: List[str]) -> str:
    return (
        f"You are a psychologist designing a short dyslexia risk screening activity for children. "
        f"Create 6 simple English word pairs appropriate for a child aged {age}. "
        f"For each pair return a JSON object with 'correct' and 'wrong'. "
        f"Difficulties to consider: {', '.join(difficulties) or 'none'}. "
        f"Return only valid JSON."
    )

# ----------------- Fallback ------------------

FALLBACK_WORD_PAIRS = [
    {"correct": "friend", "wrong": "freind"},
    {"correct": "because", "wrong": "becuase"},
    {"correct": "beautiful", "wrong": "beatiful"},
    {"correct": "tomorrow", "wrong": "tommorow"},
    {"correct": "receive", "wrong": "recieve"},
    {"correct": "different", "wrong": "diffrent"}
]

# ----------------- Endpoints ------------------

@router.post("/generate", response_model=GenerateResponse)
async def generate_words(req: GenerateRequest):

    prompt = build_generate_prompt(req.age, req.language, req.difficulties or [])

    messages = [
        {"role": "system", "content": "You are a helpful psychologist designing screening items."},
        {"role": "user", "content": prompt}
    ]

    try:
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.6,
            max_tokens=400,
        )
        text = resp.choices[0].message.content.strip()

        text_clean = re.sub(r"```(?:json)?\n", "", text)
        text_clean = re.sub(r"```$", "", text_clean)

        parsed = json.loads(text_clean)

        pairs = []
        for obj in parsed:
            if "correct" in obj and "wrong" in obj:
                pairs.append(obj)

        if not pairs:
            return {"wordPairs": FALLBACK_WORD_PAIRS}

        return {"wordPairs": pairs[:6]}

    except Exception as e:
        print("Groq error:", e)
        return {"wordPairs": FALLBACK_WORD_PAIRS}


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_results(req: AnalyzeRequest):

    attempts = req.attempts or []
    total_questions = len(attempts)
    score = sum(1 for a in attempts if a.chosenWasCorrect)
    accuracy = (score / total_questions * 100) if total_questions else 0.0

    common_mistakes = {}
    mistake_types = {}

    for a in attempts:
        if not a.chosenWasCorrect and a.chosenWord:
            key = f"{a.presentedPair.get('correct')} -> {a.chosenWord}"
            common_mistakes[key] = common_mistakes.get(key, 0) + 1

            mtype = simple_mistake_type(a.presentedPair.get("correct", ""), a.chosenWord)
            mistake_types[mtype] = mistake_types.get(mtype, 0) + 1

    times = [a.responseTimeSec for a in attempts if a.responseTimeSec]
    avg_time = statistics.mean(times) if times else None

    return {
        "score": score,
        "totalQuestions": total_questions,
        "accuracy": round(accuracy, 2),
        "commonMistakes": common_mistakes,
        "perQuestion": [
            {
                "questionIndex": a.questionIndex,
                "correct": a.presentedPair.get("correct"),
                "chosen": a.chosenWord,
                "wasCorrect": bool(a.chosenWasCorrect),
                "responseTimeSec": a.responseTimeSec
            }
            for a in attempts
        ],
        "risk": "low" if accuracy > 80 else "monitor" if accuracy > 60 else "high",
        "analysisText": None,   # AI-based long narrative removed for now
        "raw": {"mistakeTypes": mistake_types, "avgTimeSec": avg_time}
    }