from typing import Optional

import boto3
from botocore.client import Config

from storytime_common.settings import Settings


class ObjectStorage:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            config=Config(signature_version="s3v4"),
            use_ssl=settings.s3_use_ssl,
        )

    def ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._settings.s3_bucket)
        except Exception:
            self._client.create_bucket(Bucket=self._settings.s3_bucket)

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
