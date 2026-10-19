from typing import Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # minio = local Docker MinIO; aws = Amazon S3 via IAM role or default credential chain
    storage_backend: Literal["minio", "aws"] = "minio"
    s3_endpoint: Optional[str] = None
    s3_access_key: Optional[str] = None
    s3_secret_key: Optional[str] = None
    s3_bucket: str = "storytime"
    s3_region: str = "us-east-1"
    s3_use_ssl: bool = False

    script_provider: str = "stub"
    tts_provider: str = "edge"
    # Warm, clear English narrator (change if you prefer another Edge voice).
    tts_voice: str = "en-GB-SoniaNeural"
    default_template_id: str = "kids_moral_v1"

    job_key_prefix: str = "job:"
    idempotency_prefix: str = "idem:"
    artifact_url_ttl_sec: int = 3600
