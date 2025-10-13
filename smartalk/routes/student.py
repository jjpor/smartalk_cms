from fastapi import APIRouter, Depends

from smartalk.core.dynamodb import get_dynamodb_connection

router = APIRouter(prefix="/student", tags=["student"])

DBDependency = Depends(get_dynamodb_connection)
