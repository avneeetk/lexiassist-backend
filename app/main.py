# app/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse
import json
import os
from dotenv import load_dotenv
from datetime import datetime

from app.auth.routes import router as auth_router
from app.students.routes import router as students_router
from app.tests.routes import router as tests_router
from app.ai.storybook import router as storybook_router
from app.config.db import test_ai_rounds_col, test_ai_analysis_col
from app.ai import storybook as storybook_module
from app.ai.worddetective import router as worddetective_router

load_dotenv()
FRONTEND_ORIGINS = os.getenv("FRONTEND_ORIGINS", "http://localhost:5173").split(",")

app = FastAPI(title="LexiAssist Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS + ["http://localhost:5000", "http://192.168.1.2:5000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(students_router, prefix="/students", tags=["Students"])
app.include_router(tests_router, prefix="/tests", tags=["Tests"])
app.include_router(storybook_router, prefix="/api/storybook", tags=["Storybook"])
app.include_router(worddetective_router)


# --- Middleware to capture storybook AI responses ---
@app.middleware("http")
async def capture_storybook_responses(request: Request, call_next):
    # Only capture /api/storybook endpoints
    path = request.url.path
    if not path.startswith("/api/storybook/"):
        # not storybook, pass through
        return await call_next(request)

    # read request body (may be empty)
    try:
        req_body_bytes = await request.body()
        req_body = {}
        if req_body_bytes:
            try:
                req_body = json.loads(req_body_bytes.decode("utf-8"))
            except Exception:
                req_body = {}
    except Exception:
        req_body = {}

    # call downstream handler and capture response body
    response = await call_next(request)

    # We need to read the response content; if it's a StreamingResponse, buffer it.
    try:
        # response.body may not exist for streaming responses; instead read via iterator
        if hasattr(response, "body"):
            resp_body_bytes = response.body
        else:
            # fallback: collect body from iterator
            body_chunks = []
            async for chunk in response.body_iterator:
                body_chunks.append(chunk)
            resp_body_bytes = b"".join(body_chunks)
            # we must recreate the response for the client using the same body and headers
            new_response = StreamingResponse(
                iter([resp_body_bytes]), 
                status_code=response.status_code, 
                headers=dict(response.headers), 
                media_type=response.media_type
            )
            response = new_response
    except Exception:
        # if anything fails, just return the original response
        return response

    # try parse JSON response
    resp_json = None
    try:
        resp_text = resp_body_bytes.decode("utf-8")
        resp_json = json.loads(resp_text)
    except Exception:
        resp_json = None

    # Save to DB depending on the path
    now_iso = datetime.utcnow().isoformat()
    try:
        if path.endswith("/generate-rounds"):
            # store generated rounds with sessionId (if present)
            session_id = req_body.get("sessionId") if isinstance(req_body, dict) else None
            rounds_doc = {
                "sessionId": session_id,
                "request": req_body,
                "response": resp_json,
                "createdAt": now_iso,
                "path": path
            }
            test_ai_rounds_col.insert_one(rounds_doc)

        elif path.endswith("/analyze-response"):
            # store analysis with sessionId and studentId (if present)
            session_id = req_body.get("sessionId") if isinstance(req_body, dict) else None
            # try to get studentId (frontend may include it in request or not)
            student_id = req_body.get("studentId") if isinstance(req_body, dict) else None
            analysis_doc = {
                "sessionId": session_id,
                "studentId": student_id,
                "request": req_body,
                "analysis": resp_json,
                "createdAt": now_iso,
                "path": path
            }
            test_ai_analysis_col.insert_one(analysis_doc)
    except Exception as e:
        # shouldn't block the main response — log to console
        print("[capture_storybook_responses] DB write failed:", str(e))

    return response

@app.get("/")
def root():
    return {"message": "LexiAssist Backend is running 🚀"}