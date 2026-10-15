"""Schema trả về cho frontend. Tên trường camelCase, trùng src/types.ts. Các màn hình phức tạp trả dict camelCase trực tiếp."""
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class Out(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class MaCauKienOut(Out):
    id: str
    ma: str
    ten: str
    dvt: str
    dinh_muc: float
    ton_kho: float


class KhoOut(Out):
    id: str
    ten: str
    cap: str
    ton: float
    con: list["KhoOut"] | None = None
