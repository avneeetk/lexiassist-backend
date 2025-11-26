# app/auth/routes.py
from fastapi import APIRouter, Request, Response, Depends, HTTPException, status, Cookie
from fastapi.responses import JSONResponse
from app.auth.schemas import RegistrationData, LoginRequest
from app.auth.utils import hash_password, verify_password, create_access_token, decode_token, COOKIE_NAME
from app.config.db import parents_col, students_col
from app.utils.responses import success_response, error_response
from datetime import timedelta
import uuid
from pymongo.errors import DuplicateKeyError
from dotenv import load_dotenv
import os

load_dotenv()
FRONTEND_ORIGINS = os.getenv("FRONTEND_ORIGINS", "http://localhost:5173").split(",")

router = APIRouter()

# Ensure unique index on email
try:
    parents_col.create_index("email", unique=True)
except Exception:
    pass

PASSWORD_REQUIREMENTS = {
    "min_length": 8,
    "require_upper": True,
    "require_number": True,
    "require_special": True
}

def validate_password(password: str):
    errs = []
    if len(password) < PASSWORD_REQUIREMENTS["min_length"]:
        errs.append("minimum length is 8")
    if PASSWORD_REQUIREMENTS["require_upper"] and not any(c.isupper() for c in password):
        errs.append("must contain an uppercase letter")
    if PASSWORD_REQUIREMENTS["require_number"] and not any(c.isdigit() for c in password):
        errs.append("must contain a number")
    if PASSWORD_REQUIREMENTS["require_special"] and not any(c in "!@#$%^&*()-_=+[]{};:,.<>/?\\|" for c in password):
        errs.append("must contain a special character")
    return errs

@router.post("/register")
async def register(data: RegistrationData, request: Request):
    # Note: password is not part of RegistrationData per frontend. We will create a system generated password OR require frontend to collect password.
    # Based on frontend details, the UI doesn't collect password as part of the 5-step registration.
    # For now, create account with a generated random password and instruct front-end to call login flow later.
    # But we need a password for login. We'll accept an optional 'password' in request.json if frontend includes it.
    body = await request.json()
    password = body.get("password")
    if not password:
        # create a random strong password (user should reset later) — better to ask frontend to collect password in signup flow.
        import secrets, string
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*()"
        password = ''.join(secrets.choice(alphabet) for _ in range(12))

    pw_errs = validate_password(password)
    if pw_errs:
        payload, code = error_response(
            "Password does not meet requirements",
            code="PASSWORD_INVALID",
            errors={"password": " and ".join(pw_errs)},
            status_code=400,
        )
        return JSONResponse(content=payload, status_code=400)

    parent_doc = {
        "parentName": data.parentName,
        "relationship": data.relationship,
        "email": data.email.lower(),
        "mobile": data.mobile or "",
        "preferredLanguage": data.preferredLanguage,
        "password_hash": hash_password(password),
        "createdAt": __import__("datetime").datetime.utcnow().isoformat()
    }
    try:
        res = parents_col.insert_one(parent_doc)
        parent_id = str(res.inserted_id)
    except Exception as e:
        # likely duplicate email
        payload, code = error_response("Email already registered", code="EMAIL_EXISTS", errors={"email": "Email already in use"}, status_code=409)
        return JSONResponse(content=payload, status_code=409)

    # create student record
    student_doc = {
        "parentId": parent_id,
        "childName": data.childName,
        "childAge": data.childAge,
        "childGrade": data.childGrade,
        "primaryLanguage": data.primaryLanguage,
        "languagesCanRead": data.languagesCanRead,

        "strugglingWithReading": data.strugglingWithReading,
        "letterMixups": data.letterMixups,
        "feelingAboutReading": data.feelingAboutReading,
        "teacherMentioned": data.teacherMentioned,
        "difficultySpelling": data.difficultySpelling,
        "prefersListening": data.prefersListening,

        "problemsSince": data.problemsSince,
        "problemAreas": data.problemAreas,
        "additionalInfo": data.additionalInfo or "",
        "consentAnalysis": data.consentAnalysis,
        "createdAt": __import__("datetime").datetime.utcnow().isoformat()
    }
    stud_res = students_col.insert_one(student_doc)
    student_id = str(stud_res.inserted_id)

    # create JWT and set cookie
    token, expiry_iso = create_access_token(subject=parent_id, expires_delta=timedelta(minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))))

    response_payload, status_code = success_response("Registration successful", data={"parentId": parent_id, "studentId": student_id})
    response = JSONResponse(content=response_payload, status_code=201)
    # set cookie
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=False,  # set to True in production with HTTPS
        samesite="lax",
        max_age=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")) * 60,
        path="/"
        # Don't set domain for localhost
    )
    return response

@router.post("/login")
async def login(login_req: LoginRequest):
    email = login_req.email.lower()
    parent = parents_col.find_one({"email": email})
    if not parent:
        payload, _ = error_response("Invalid credentials", code="INVALID_CREDENTIALS", status_code=401)
        return JSONResponse(content=payload, status_code=401)

    if not verify_password(login_req.password, parent.get("password_hash", "")):
        payload, _ = error_response("Invalid credentials", code="INVALID_CREDENTIALS", status_code=401)
        return JSONResponse(content=payload, status_code=401)

    parent_id = str(parent["_id"])
    token, expiry_iso = create_access_token(subject=parent_id)
    payload, _ = success_response("Login successful", data={"parentId": parent_id})
    response = JSONResponse(content=payload, status_code=200)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=False,  # set to True in production with HTTPS
        samesite="lax",
        max_age=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")) * 60,
        path="/"
        # Don't set domain for localhost
    )
    return response

@router.get("/me")
async def me(session_token: str | None = Cookie(default=None, alias=COOKIE_NAME)):
    if not session_token:
        payload, _ = error_response("Not authenticated", code="NOT_AUTHENTICATED", status_code=401)
        return JSONResponse(content=payload, status_code=401)
    try:
        decoded = decode_token(session_token)
        parent_id = decoded.get("sub")
        parent = parents_col.find_one({"_id": __import__("bson").ObjectId(parent_id)})
        if not parent:
            payload, _ = error_response("User not found", code="NOT_FOUND", status_code=404)
            return JSONResponse(content=payload, status_code=404)

        # minimal payload as requested
        data = {
            "id": str(parent["_id"]),
            "parentName": parent.get("parentName"),
            "email": parent.get("email"),
            "preferredLanguage": parent.get("preferredLanguage")
        }
        return JSONResponse(content={"data": data}, status_code=200)
    except Exception as e:
        payload, _ = error_response("Not authenticated", code="INVALID_TOKEN", status_code=401)
        return JSONResponse(content=payload, status_code=401)