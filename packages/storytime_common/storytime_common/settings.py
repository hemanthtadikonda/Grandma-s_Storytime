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

    # stub = rules only; ollama = local Ollama; openai_compatible = vLLM, LocalAI, etc.
    script_provider: Literal["stub", "ollama", "openai_compatible"] = "stub"
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.2:3b"
    llm_openai_base_url: str = "http://localhost:8080"
    llm_api_key: Optional[str] = None
    llm_timeout_sec: int = 180
    llm_max_tokens: int = 1200
    llm_temperature: float = 0.4

    tts_provider: str = "edge"
    # Warm, clear English narrator (change if you prefer another Edge voice).
    tts_voice: str = "en-GB-SoniaNeural"
    default_template_id: str = "kids_moral_v1"

    # Scene images: search per prompt, download to temp dir, delete after job
    image_provider: Literal["none", "wikimedia", "pexels", "pixabay"] = "wikimedia"
    pexels_api_key: Optional[str] = None
    pixabay_api_key: Optional[str] = None
    image_search_timeout_sec: int = 25
    image_max_bytes: int = 8_000_000
    image_target_width: int = 1080
    image_target_height: int = 1920

    job_key_prefix: str = "job:"
    idempotency_prefix: str = "idem:"
    artifact_url_ttl_sec: int = 3600
