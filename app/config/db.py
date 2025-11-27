# app/config/db.py
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client["lexiassist-b"]

# Collections
parents_col = db["parents"]
students_col = db["students"]
tests_col = db["tests"]
test_ai_rounds_col = db["test_ai_rounds"]
test_ai_analysis_col = db["test_ai_analysis"]

try:
    test_ai_rounds_col.create_index([("sessionId", 1)])
    test_ai_rounds_col.create_index([("createdAt", -1)])
    test_ai_analysis_col.create_index([("sessionId", 1)])
    test_ai_analysis_col.create_index([("studentId", 1), ("createdAt", -1)])
except Exception:
    pass