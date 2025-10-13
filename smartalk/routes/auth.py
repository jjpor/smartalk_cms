import datetime
import uuid
from typing import Optional

import google.auth.transport.requests
import google.oauth2.id_token
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr

from smartalk.core.dynamodb import get_dynamodb_connection
from smartalk.core.settings import settings
from smartalk.db_usage.dynamodb_auth import (
    create_user_if_not_exists,
    get_user_by_email,
    normalize_email,
)

router = APIRouter(prefix="/auth", tags=["auth"])

# Uso della Dependency Injection per ottenere la connessione resiliente
DBDependency = Depends(get_dynamodb_connection)
# -------------------------------------------------
# SCHEMI Pydantic
# -------------------------------------------------


class AuthRequest(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    password: Optional[str] = None


class GoogleLoginRequest(BaseModel):
    credential: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: EmailStr
    name: str


# -------------------------------------------------
# UTILITY TOKEN
# -------------------------------------------------


def create_jwt_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7),
        "iat": datetime.datetime.now(datetime.timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALG)


def decode_jwt_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(request: Request):
    """
    Dipendenza FastAPI per ottenere l’utente autenticato dal JWT.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    token = auth_header.split(" ")[1]
    payload = decode_jwt_token(token)
    user_id = payload.get("sub")
    email = payload.get("email")

    if not user_id or not email:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = await get_user_by_email(email, DBDependency)
    if not user or user.get("id") != user_id:
        raise HTTPException(status_code=401, detail="User not found")

    return user


# -------------------------------------------------
# AUTH ENDPOINTS
# -------------------------------------------------


@router.post("/signup", response_model=TokenResponse)
async def signup(req: AuthRequest):
    """
    Crea un nuovo utente se non esiste già (signup tradizionale).
    """
    email = normalize_email(req.email)
    existing = await get_user_by_email(email, DBDependency)

    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    # genera user_id stabile
    user_id = f"u_{uuid.uuid4().hex[:10]}"

    user = await create_user_if_not_exists(user_id, email, req.name or email, DBDependency)
    token = create_jwt_token(user_id, email)

    return TokenResponse(
        access_token=token,
        user_id=user_id,
        email=email,
        name=user["name"],
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: AuthRequest):
    """
    Login classico basato su email (senza password per ora).
    """
    email = normalize_email(req.email)
    user = await get_user_by_email(email, DBDependency)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    token = create_jwt_token(user["id"], email)
    return TokenResponse(
        access_token=token,
        user_id=user["id"],
        email=email,
        name=user["name"],
    )


@router.post("/google", response_model=TokenResponse)
async def login_with_google(req: GoogleLoginRequest):
    """
    Login con Google OAuth (client → token credential → verify).
    """
    try:
        id_info = google.oauth2.id_token.verify_oauth2_token(
            req.credential,
            google.auth.transport.requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {e}")

    email = normalize_email(id_info["email"])
    name = id_info.get("name", email)

    # Recupera o crea user
    user = await get_user_by_email(email, DBDependency)
    if not user:
        user_id = f"u_{uuid.uuid4().hex[:10]}"
        user = await create_user_if_not_exists(user_id, email, name, DBDependency)
    else:
        user_id = user["id"]

    token = create_jwt_token(user_id, email)

    return TokenResponse(
        access_token=token,
        user_id=user_id,
        email=email,
        name=user.get("name", name),
    )


# -------------------------------------------------
# PASSWORD RESET (PLACEHOLDER)
# -------------------------------------------------


@router.post("/forgot")
async def forgot_password(req: AuthRequest):
    """
    Placeholder: invio email reset (non implementato).
    """
    email = normalize_email(req.email)
    user = await get_user_by_email(email, DBDependency)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # TODO: invia email reset (in futuro)
    return {"message": f"Password reset email sent to {email}"}
