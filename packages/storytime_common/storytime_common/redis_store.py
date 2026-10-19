import json
from typing import Optional

import redis

from storytime_common.models import JobRecord
from storytime_common.settings import Settings


class JobStore:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._r = redis.from_url(settings.redis_url, decode_responses=True)

    def _job_key(self, job_id: str) -> str:
        return f"{self._settings.job_key_prefix}{job_id}"

    def _idem_key(self, idem: str) -> str:
        return f"{self._settings.idempotency_prefix}{idem}"

    def save(self, job: JobRecord) -> None:
        self._r.set(self._job_key(job.id), job.model_dump_json())
        self._r.set(self._idem_key(job.idempotency_key), job.id)

    def get(self, job_id: str) -> Optional[JobRecord]:
        raw = self._r.get(self._job_key(job_id))
        if not raw:
            return None
        return JobRecord.model_validate_json(raw)

    def get_by_idempotency(self, idem: str) -> Optional[JobRecord]:
        job_id = self._r.get(self._idem_key(idem))
        if not job_id:
            return None
        return self.get(job_id)

    def update(self, job: JobRecord) -> None:
        self.save(job)
