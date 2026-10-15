from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .db import SessionLocal, get_session
from .routers import (admin, anh, auth, cot, doi_soat, du_an, hien_truong, qaqc, quy_tac, tai_lieu, thong_bao, tim_kiem,
                      vat_tu)
from .services import storage
from .services.ref_data import ensure_reference_data


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with SessionLocal() as s:
        await ensure_reference_data(s)
    await storage.ensure_bucket()
    yield


prod = settings.env == "production"
app = FastAPI(title="TuyếnSố API", version="0.1.0", lifespan=lifespan,
              docs_url=None if prod else "/api/docs", redoc_url=None, openapi_url=None if prod else "/api/openapi.json")

if settings.cors_origins:
    app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
                       allow_credentials=True, allow_methods=["*"], allow_headers=["Authorization", "Content-Type", "X-Du-An"])

api = APIRouter(prefix="/api")
for r in (auth.router, du_an.router, admin.router, cot.router, quy_tac.router, qaqc.router, doi_soat.router, vat_tu.router,
          hien_truong.router, anh.router, tai_lieu.router, thong_bao.router, tim_kiem.router):
    api.include_router(r)


@api.get("/health", tags=["he-thong"])
async def health(s: AsyncSession = Depends(get_session)):
    await s.execute(text("SELECT 1"))
    return {"status": "ok"}


app.include_router(api)
