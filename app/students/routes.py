# app/students/routes.py
from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId
from app.config.db import students_col
from app.students.schemas import StudentCreate, StudentUpdate
from app.auth.dependencies import get_current_parent
from app.utils.responses import success_response, error_response
from fastapi.responses import JSONResponse

router = APIRouter()

@router.post("/")
def create_student(data: StudentCreate, parent_data = Depends(get_current_parent)):
    parent_id, _ = parent_data

    student_doc = data.dict()
    student_doc["parentId"] = parent_id
    student_doc["createdAt"] = __import__("datetime").datetime.utcnow().isoformat()

    res = students_col.insert_one(student_doc)

    payload, _ = success_response(
        "Student created successfully",
        data={"studentId": str(res.inserted_id)}
    )
    return JSONResponse(content=payload, status_code=201)


@router.get("/")
def list_students(parent_data = Depends(get_current_parent)):
    parent_id, _ = parent_data

    cursor = students_col.find({"parentId": parent_id})
    students = []

    for s in cursor:
        s["_id"] = str(s["_id"])
        students.append(s)

    return {"data": students}


@router.get("/{student_id}")
def get_student(student_id: str, parent_data = Depends(get_current_parent)):
    parent_id, _ = parent_data

    student = students_col.find_one({"_id": ObjectId(student_id), "parentId": parent_id})
    if not student:
        payload, _ = error_response("Student not found", code="STUDENT_NOT_FOUND", status_code=404)
        return JSONResponse(content=payload, status_code=404)

    student["_id"] = str(student["_id"])
    return {"data": student}


@router.put("/{student_id}")
def update_student(student_id: str, data: StudentUpdate, parent_data = Depends(get_current_parent)):
    parent_id, _ = parent_data

    update = {k: v for k, v in data.dict().items() if v is not None}

    res = students_col.update_one(
        {"_id": ObjectId(student_id), "parentId": parent_id},
        {"$set": update}
    )

    if res.matched_count == 0:
        payload, _ = error_response("Student not found", code="STUDENT_NOT_FOUND", status_code=404)
        return JSONResponse(content=payload, status_code=404)

    payload, _ = success_response("Student updated successfully")
    return JSONResponse(content=payload, status_code=200)


@router.delete("/{student_id}")
def delete_student(student_id: str, parent_data = Depends(get_current_parent)):
    parent_id, _ = parent_data

    res = students_col.delete_one({"_id": ObjectId(student_id), "parentId": parent_id})

    if res.deleted_count == 0:
        payload, _ = error_response("Student not found", code="STUDENT_NOT_FOUND", status_code=404)
        return JSONResponse(content=payload, status_code=404)

    payload, _ = success_response("Student deleted successfully")
    return JSONResponse(content=payload, status_code=200)