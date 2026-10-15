import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AuditLog


def ghi(s: AsyncSession, *, nguoi_id: uuid.UUID | None, du_an_id: uuid.UUID | None, hanh_dong: str, bang: str,
        doi_tuong_id: Any = None, truoc: Any = None, sau: Any = None) -> None:
    s.add(AuditLog(nguoi_dung_id=nguoi_id, du_an_id=du_an_id, hanh_dong=hanh_dong, bang=bang,
                   doi_tuong_id=str(doi_tuong_id) if doi_tuong_id is not None else None, truoc=truoc, sau=sau))
