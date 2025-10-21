import datetime
import uuid
from typing import Any, Dict, Optional

import google.auth.transport.requests
import google.oauth2.id_token
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr

from smartalk.core.dynamodb import get_dynamodb_connection
from smartalk.core.settings import settings
from smartalk.db_usage.dynamodb_auth import (
    create_user_if_not_exists,
    get_user_by_email,
    normalize_email,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

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
    email: EmailStr
    name: str


# -------------------------------------------------
# UTILITY TOKEN
# -------------------------------------------------


def create_jwt_token(user_id: str, email: str, user_type: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "user_type": user_type,
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1),
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


async def get_current_user(request: Request, DBDependency: Any = DBDependency):
    """
    Dipendenza FastAPI per ottenere l'utente autenticato dal JWT.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    token = auth_header.split(" ")[1]
    payload = decode_jwt_token(token)
    user_id = payload.get("sub")
    email = payload.get("email")
    user_type = payload.get("user_type")

    if not user_id or not email or not user_type:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = await get_user_by_email(email, DBDependency)
    if not user or user.get("id") != user_id or user.get("user_type") != user_type:
        raise HTTPException(status_code=401, detail="User not found")

    return user

# ====================================================================
# UTILITY PER IL REFRESH E RISPOSTA
# ====================================================================

def create_token_response(data: Any, user_data: Dict[str, Any]) -> JSONResponse:
    """
    Crea una JSONResponse, aggiungendo un nuovo token nell'header X-New-Auth-Token.
    Utilizza i campi 'id', 'email', 'user_type' dall'oggetto utente completo.
    """
    user_id = user_data.get("id")
    email = user_data.get("email")
    user_type = user_data.get("user_type")

    if not user_id or not email or not user_type:
        raise HTTPException(status_code=500, detail="Internal error: User data missing fields for token refresh.")

    # Emettiamo un nuovo token utilizzando la firma esatta di create_jwt_token
    new_token = create_jwt_token(user_id, email, user_type)
    
    response = JSONResponse(
        content={"success": True, **data},
        headers={"X-New-Auth-Token": new_token}
    )
    return response

# -------------------------------------------------
# AUTH ENDPOINTS
# -------------------------------------------------

'''
@router.post("/signup", response_model=TokenResponse)
async def signup(req: AuthRequest, DBDependency: Any = DBDependency):
    """
    Crea un nuovo utente se non esiste già (signup tradizionale).
    """
    email = normalize_email(req.email)
    existing = await get_user_by_email(email, DBDependency)

    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    user = await create_user_if_not_exists(email, req.name or email, req.password, DBDependency)
    token = create_jwt_token(user["id"], email, user["user_type"])

    return TokenResponse(
        access_token=token,
        email=email,
        name=user["name"],
    )
'''

@router.post("/login", response_model=TokenResponse)
async def login(req: AuthRequest, DBDependency: Any = DBDependency):
    """
    Login classico basato su email e password.
    """
    email = normalize_email(req.email)
    user = await get_user_by_email(email, DBDependency)

    # Errore se non esiste o la password non è corretta
    if not user:
        raise HTTPException(status_code=404, detail="Wrong credentials.")
    else:
        if not verify_password(req.password, user["password_hash"]):
            raise HTTPException(status_code=404, detail="Wrong credentials.")

    token = create_jwt_token(user["id"], email, user["user_type"])
    return TokenResponse(
        access_token=token,
        email=email,
        name=user["name"],
    )


@router.post("/google", response_model=TokenResponse)
async def login_with_google(req: GoogleLoginRequest, DBDependency: Any = DBDependency):
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
        # Crea un user con una nuova password
        #password = f"{uuid.uuid4().hex[:8]}"
        #user = await create_user_if_not_exists(email, name, password, DBDependency)
        # TODO: invia email per fargli conoscere la sua password se vuole accedere in modo tradizionale
        raise HTTPException(status_code=401, detail="Invalid Login")

    token = create_jwt_token(user["id"], email, user["user_type"])

    return TokenResponse(
        access_token=token,
        email=email,
        name=user.get("name", name),
    )


# -------------------------------------------------
# PASSWORD RESET (PLACEHOLDER)
# -------------------------------------------------

'''
@router.post("/forgot")
async def forgot_password(req: AuthRequest, DBDependency: Any = DBDependency):
    """
    Placeholder: invio email reset (non implementato).
    """
    email = normalize_email(req.email)
    user = await get_user_by_email(email, DBDependency)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # TODO: invia email reset (in futuro)
    return {"message": f"Password reset email sent to {email}"}
'''