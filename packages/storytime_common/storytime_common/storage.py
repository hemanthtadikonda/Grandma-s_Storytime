from typing import Any, Optional

import boto3
from botocore.client import Config

from storytime_common.settings import Settings


class ObjectStorage:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._client = self._build_client(settings)

    @staticmethod
    def _build_client(settings: Settings):
        kwargs: dict[str, Any] = {
            "service_name": "s3",
            "region_name": settings.s3_region,
            "config": Config(signature_version="s3v4"),
        }

        if settings.storage_backend == "minio":
            if not settings.s3_endpoint:
                raise ValueError("S3_ENDPOINT is required when STORAGE_BACKEND=minio")
            if not settings.s3_access_key or not settings.s3_secret_key:
                raise ValueError("S3_ACCESS_KEY and S3_SECRET_KEY are required when STORAGE_BACKEND=minio")
            kwargs["endpoint_url"] = settings.s3_endpoint
            kwargs["use_ssl"] = settings.s3_use_ssl
            kwargs["aws_access_key_id"] = settings.s3_access_key
            kwargs["aws_secret_access_key"] = settings.s3_secret_key
            return boto3.client(**kwargs)

        # AWS S3: use instance profile / task role / env when keys are omitted
        if settings.s3_access_key and settings.s3_secret_key:
            kwargs["aws_access_key_id"] = settings.s3_access_key
            kwargs["aws_secret_access_key"] = settings.s3_secret_key
        return boto3.client(**kwargs)

    def ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._settings.s3_bucket)
        except Exception as exc:
            if self._settings.storage_backend == "minio":
                self._client.create_bucket(Bucket=self._settings.s3_bucket)
                return
            raise RuntimeError(
                f"Cannot access S3 bucket '{self._settings.s3_bucket}'. "
                "Create the bucket in AWS and attach an IAM role with s3:PutObject / s3:GetObject."
            ) from exc

    def upload_file(self, local_path: str, key: str, content_type: str = "video/mp4") -> int:
        self.ensure_bucket()
        self._client.upload_file(
            local_path,
            self._settings.s3_bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )
        head = self._client.head_object(Bucket=self._settings.s3_bucket, Key=key)
        return int(head["ContentLength"])

    def presigned_get(self, key: str, expires_sec: Optional[int] = None) -> str:
        ttl = expires_sec or self._settings.artifact_url_ttl_sec
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._settings.s3_bucket, "Key": key},
            ExpiresIn=ttl,
        )
