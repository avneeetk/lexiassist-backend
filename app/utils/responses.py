# app/utils/responses.py
from fastapi import Response

def success_response(message: str = "Success", data: dict | None = None, status_code: int = 200):
    payload = {"success": True, "message": message}
    if data is not None:
        payload["data"] = data
    return payload, status_code

def error_response(message: str = "Error", code: str | None = None, errors: dict | None = None, status_code: int = 400):
    payload = {"success": False, "message": message}
    if code:
        payload["code"] = code
    if errors:
        payload["errors"] = errors
    return payload, status_code