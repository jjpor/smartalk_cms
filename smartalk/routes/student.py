from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, constr

from smartalk.routes.auth import get_current_user

router = APIRouter(prefix="/student", tags=["student"])
