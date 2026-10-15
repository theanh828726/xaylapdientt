from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "dev"
    database_url: str
    jwt_secret: str
    access_ttl_min: int = 15
    refresh_ttl_days: int = 14
    cookie_secure: bool = False
    cors_origins: str = ""
    seed_demo_password: str = ""
    minio_endpoint: str = "minio:9000"
    minio_root_user: str
    minio_root_password: str
    minio_bucket: str = "tuyenso"
    minio_secure: bool = False

    @field_validator("jwt_secret")
    @classmethod
    def _jwt_dai_du(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("JWT_SECRET phải dài ít nhất 32 ký tự")
        return v


settings = Settings()
