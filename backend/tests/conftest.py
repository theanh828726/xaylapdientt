"""Test chạy trên DB riêng `tuyenso_test` (tạo mới mỗi phiên): migration thật + seed demo."""
import os
import subprocess
import uuid

import asyncpg
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import make_url

_base = make_url(os.environ["DATABASE_URL"])
TEST_DB = "tuyenso_test"
os.environ["DATABASE_URL"] = _base.set(database=TEST_DB).render_as_string(hide_password=False)
os.environ["ENV"] = "test"
os.environ["MINIO_BUCKET"] = "tuyenso-test"   # không đụng dữ liệu thật
os.environ.setdefault("SEED_DEMO_PASSWORD", "DemoTuyenSo#2026")
PW = os.environ["SEED_DEMO_PASSWORD"]


@pytest_asyncio.fixture(scope="session", loop_scope="session", autouse=True)
async def _db():
    admin = await asyncpg.connect(user=_base.username, password=_base.password, host=_base.host,
                                  port=_base.port or 5432, database=_base.database)
    await admin.execute(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)")
    await admin.execute(f"CREATE DATABASE {TEST_DB}")
    await admin.close()
    subprocess.run(["alembic", "upgrade", "head"], check=True, env=os.environ)
    from app.db import SessionLocal
    from app.seed_demo import nap
    from app.services import storage
    await storage.ensure_bucket()
    async with SessionLocal() as s:
        await nap(s)
    yield


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def client():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def H(client):
    """Header đăng nhập theo từng tài khoản demo: H['kythuat']."""
    out = {}
    for who in ["giamdoc", "chihuytruong", "kythuat", "ketoan", "kehoach", "phogiamdoc", "chutich", "tam", "khoa", "son"]:
        r = await client.post("/api/auth/login", json={"email": f"{who}@demo.tuyenso.local", "matKhau": PW})
        assert r.status_code == 200, r.text
        out[who] = {"Authorization": f"Bearer {r.json()['accessToken']}"}
    return out


def new_id() -> str:
    return str(uuid.uuid4())
