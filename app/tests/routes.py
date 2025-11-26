# app/tests/routes.py
from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.responses import JSONResponse
from app.tests.schemas import TestSubmitUnion
from app.utils.responses import success_response, error_response
from app.config.db import students_col, tests_col
from app.auth.dependencies import get_current_parent
from bson import ObjectId
from datetime import datetime
from typing import Optional

router = APIRouter()

# ensure tests collection exists
try:
    tests_col.create_index([("studentId", 1), ("testType", 1), ("createdAt", -1)])
except Exception:
    pass


@router.post("/submit")
def submit_test(payload: TestSubmitUnion, parent=Depends(get_current_parent)):
    """
    Generic test submission endpoint.
    Frontend sends: { testType, studentId, results, metadata?, questionData?, roundData?, wordPairs? }
    """
    parent_id, _ = parent

    # validate student belongs to parent
    try:
        student = students_col.find_one({
            "_id": ObjectId(payload.studentId),
            "parentId": parent_id
        })
    except Exception:
        student = None

    if not student:
        body, _ = error_response(
            "Student not found or not owned by authenticated parent",
            code="STUDENT_NOT_FOUND",
            status_code=404
        )
        return JSONResponse(content=body, status_code=404)

    doc = {
        "studentId": payload.studentId,
        "testType": payload.testType,
        "results": payload.results,
        "metadata": payload.metadata or {},
        "questionData": payload.questionData or [],
        "roundData": payload.roundData or {},
        "wordPairs": payload.wordPairs or [],
        "createdAt": datetime.utcnow().isoformat()
    }

    # Before inserting, if this is a storybook, try to find server-side analysis
    server_ai_analysis = None
    try:
        # 1) prefer sessionId if frontend supplied it in payload.results
        session_id = None
        if isinstance(payload.results, dict):
            session_id = payload.results.get("sessionId")

        if session_id:
            server_ai_analysis = test_ai_analysis_col.find_one({"sessionId": session_id}, sort=[("createdAt", -1)])
        else:
            # fallback: find recent analysis for this student
            # match by studentId in analysis documents
            server_ai_analysis = test_ai_analysis_col.find_one(
                {"studentId": payload.studentId},
                sort=[("createdAt", -1)]
            )
    except Exception:
        server_ai_analysis = None

    if server_ai_analysis and server_ai_analysis.get("analysis"):
        # overwrite/attach trusted analysis
        doc["aiAnalysis"] = server_ai_analysis["analysis"]
    else:
        # if frontend provided aiAnalysis, still store it but mark it as 'source:frontend'
        if isinstance(payload.results, dict) and payload.results.get("aiAnalysis"):
            doc["aiAnalysis"] = {
                "source": "frontend",
                "analysis": payload.results.get("aiAnalysis")
            }

    # insert the test doc
    inserted = tests_col.insert_one(doc)
    test_id = str(inserted.inserted_id)

    body, _ = success_response("Test submitted", data={"testId": test_id})
    return JSONResponse(content=body, status_code=201)


@router.get("/history")
def get_history(
    parent=Depends(get_current_parent),
    testType: Optional[str] = Query(None, description="Filter by testType"),
    limit: int = Query(20, gt=0, le=200),
    offset: int = Query(0, ge=0)
):
    """
    Return test history for the authenticated parent's students.
    Filters by testType if provided. Paginated by limit/offset.
    """
    parent_id, _ = parent

    # get all student IDs for the parent
    cursor_students = students_col.find({"parentId": parent_id}, {"_id": 1})
    student_ids = [str(s["_id"]) for s in cursor_students]

    query = {"studentId": {"$in": student_ids}}
    if testType:
        query["testType"] = testType

    total = tests_col.count_documents(query)
    docs = tests_col.find(query).sort("createdAt", -1).skip(offset).limit(limit)

    results = []
    for d in docs:
        d["id"] = str(d["_id"])
        d.pop("_id", None)
        results.append(d)

    return JSONResponse(content={"data": {"total": total, "tests": results}}, status_code=200)


@router.get("/{test_id}")
def get_test_detail(test_id: str, parent=Depends(get_current_parent)):
    """
    Get full test document if it belongs to authenticated parent.
    """
    parent_id, _ = parent

    doc = tests_col.find_one({"_id": ObjectId(test_id)})
    if not doc:
        body, _ = error_response("Test not found", code="TEST_NOT_FOUND", status_code=404)
        return JSONResponse(content=body, status_code=404)

    # ensure student ownership
    student = students_col.find_one({"_id": ObjectId(doc["studentId"])})
    if not student or student.get("parentId") != parent_id:
        body, _ = error_response("Not authorized to view this test", code="NOT_AUTHORIZED", status_code=403)
        return JSONResponse(content=body, status_code=403)

    doc["id"] = str(doc["_id"])
    doc.pop("_id", None)
    return JSONResponse(content={"data": doc}, status_code=200)


# ------------------------------------------------------------------
# Storybook AI placeholder routes (to be replaced with real AI routes)
# ------------------------------------------------------------------

@router.post("/storybook/generate-rounds")
def storybook_generate(payload: dict, parent=Depends(get_current_parent)):
    """
    Placeholder: frontend will call to request AI-generated rounds after round3.
    """
    mock_rounds = {
        "round4": {"items": ["A", "B", "C"], "instructions": "Arrange these..."},
        "round5": {"items": ["D", "E", "F"], "instructions": "Arrange these..."}
    }
    return JSONResponse(content={"data": mock_rounds}, status_code=200)


@router.post("/storybook/analyze-response")
def storybook_analyze(payload: dict, parent=Depends(get_current_parent)):
    """
    Placeholder: accept final storybook submission and return mock analysis.
    """
    mock_analysis = {
        "summary": "Sample analysis",
        "riskLevel": "low",
        "patterns": {"sequencing": "ok"}
    }
    return JSONResponse(content={"data": mock_analysis}, status_code=200)