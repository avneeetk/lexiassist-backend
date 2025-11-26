# app/auth/dependencies.py
from fastapi import Cookie, HTTPException, status
from app.auth.utils import decode_token, COOKIE_NAME
from app.config.db import parents_col
from bson import ObjectId

def get_current_parent(session_token: str = Cookie(default=None, alias=COOKIE_NAME)):
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    try:
        payload = decode_token(session_token)
        parent_id = payload.get("sub")
        if not parent_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        parent = parents_col.find_one({"_id": ObjectId(parent_id)})
        if not parent:
            raise HTTPException(status_code=404, detail="Parent not found")

        return str(parent["_id"]), parent

    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")