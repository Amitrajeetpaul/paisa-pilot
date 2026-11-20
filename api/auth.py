"""Sign-in: the browser signs in with Google Identity Platform (email + password) and sends the ID token
as `Authorization: Bearer ...`. We verify its signature, issuer and audience here; we never see or store
a password. The uid inside the token is the only thing that decides whose data a request can touch.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from fastapi import Header, HTTPException


@dataclass(frozen=True)
class AuthUser:
    uid: str
    email: str | None


def _project() -> str | None:
    return os.environ.get("AUTH_PROJECT") or os.environ.get("FIRESTORE_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT")


def verify_token(token: str) -> dict:
    """Verify a Firebase/Identity Platform ID token and return its claims. Replaced in tests."""
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token

    project = _project()
    if not project:
        raise ValueError("AUTH_PROJECT is not set")
    return id_token.verify_firebase_token(token, google_requests.Request(), audience=project)


def _user_from_header(authorization: str | None) -> AuthUser | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization[7:].strip()
    if not token:
        return None
    try:
        claims = verify_token(token)
    except Exception:  # noqa: BLE001 - expired, forged or malformed all mean "not signed in"
        return None
    uid = claims.get("user_id") or claims.get("sub")
    if not uid:
        return None
    return AuthUser(uid=str(uid), email=claims.get("email"))


def optional_user(authorization: str | None = Header(default=None)) -> AuthUser | None:
    return _user_from_header(authorization)


def require_user(authorization: str | None = Header(default=None)) -> AuthUser:
    user = _user_from_header(authorization)
    if user is None:
        raise HTTPException(status_code=401, detail={"code": "not_signed_in", "message": "Please sign in again."})
    return user
