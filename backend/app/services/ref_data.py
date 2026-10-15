"""Dữ liệu tham chiếu nạp khi khởi động: danh mục rule (ghi đè) và quyền mặc định (chỉ khi bảng còn trống)."""
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import MucRule, RolePermission, RuleDef
from ..rbac import DEFAULT_PERMS
from ..rules_data import RULES


async def ensure_reference_data(s: AsyncSession) -> None:
    for ma, ten, muc, module in RULES:
        stmt = insert(RuleDef).values(ma=ma, ten=ten, muc=MucRule(muc), module=module, mo_ta=f"Nhóm hồ sơ {module}")
        await s.execute(stmt.on_conflict_do_update(
            index_elements=["ma"], set_={"ten": ten, "muc": MucRule(muc), "module": module, "mo_ta": f"Nhóm hồ sơ {module}"}))
    if not await s.scalar(select(func.count()).select_from(RolePermission)):
        s.add_all(RolePermission(vai_tro=r, quyen=str(p)) for r, perms in DEFAULT_PERMS.items() for p in perms)
    await s.commit()
