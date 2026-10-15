import asyncio

from alembic import context
from geoalchemy2 import alembic_helpers
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from app.models import Base

target_metadata = Base.metadata


def _include_object(obj, name, type_, reflected, compare_to):
    # Image PostGIS có sẵn bảng tiger/topology/spatial_ref_sys: chỉ quản lý bảng của ta, không bao giờ DROP bảng lạ.
    if type_ == "table" and reflected and name not in target_metadata.tables:
        return False
    if type_ in ("index", "unique_constraint", "foreign_key_constraint", "column") and reflected:
        table = getattr(obj, "table", None)
        if table is not None and table.name not in target_metadata.tables:
            return False
    return alembic_helpers.include_object(obj, name, type_, reflected, compare_to)


_opts = dict(
    target_metadata=target_metadata,
    compare_type=True,
    include_object=_include_object,
    process_revision_directives=alembic_helpers.writer,
    render_item=alembic_helpers.render_item,
)


def _run(connection) -> None:
    context.configure(connection=connection, **_opts)
    with context.begin_transaction():
        context.run_migrations()


async def _online() -> None:
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as conn:
        await conn.run_sync(_run)
    await engine.dispose()


if context.is_offline_mode():
    context.configure(url=settings.database_url, literal_binds=True, **_opts)
    with context.begin_transaction():
        context.run_migrations()
else:
    asyncio.run(_online())
