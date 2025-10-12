from contextlib import asynccontextmanager

from fastapi import FastAPI

from smartalk.routes import auth, student
from smartalk.scripts.create_tables import ensure_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    # crea tabelle su avvio
    await ensure_tables()
    yield


app = FastAPI(title="Smartalk CMS", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(student.router)
