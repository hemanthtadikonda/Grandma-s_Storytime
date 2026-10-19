import uuid

from celery import Celery
from fastapi import FastAPI, HTTPException

from storytime_common.idempotency import prompt_hash
from storytime_common.models import (
    ArtifactResponse,
    JobRecord,
    JobResponse,
    JobStatus,
    SubmitJobRequest,
)
from storytime_common.redis_store import JobStore
from storytime_common.settings import Settings
from storytime_common.storage import ObjectStorage

settings = Settings()
store = JobStore(settings)
storage = ObjectStorage(settings)

celery = Celery("storytime", broker=settings.celery_broker_url, backend=settings.celery_result_backend)

app = FastAPI(
    title="Grandma's Storytime API",
    version="0.1.0",
    description="Async kids-short video pipeline: submit job → poll status → download MP4.",
)


def _job_to_response(job: JobRecord, cached: bool = False) -> JobResponse:
    download_url = None
    artifact_id = None
    if job.status == JobStatus.done and job.artifact_key:
        artifact_id = job.id
        download_url = storage.presigned_get(job.artifact_key)
    return JobResponse(
        id=job.id,
        status=job.status,
        created_at=job.created_at,
        updated_at=job.updated_at,
        error=job.error,
        artifact_id=artifact_id,
        download_url=download_url,
        cached=cached,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/jobs", response_model=JobResponse, status_code=202)
def create_job(body: SubmitJobRequest) -> JobResponse:
    idem = body.idempotency_key or prompt_hash(
        body.prompt, body.template_id, body.duration_target_sec
    )
    existing = store.get_by_idempotency(idem)
    if existing and existing.status == JobStatus.done:
        return _job_to_response(existing, cached=True)
    if existing and existing.status not in (JobStatus.failed,):
        return _job_to_response(existing, cached=False)

    now = JobRecord.now()
    job_id = str(uuid.uuid4())
    job = JobRecord(
        id=job_id,
        status=JobStatus.queued,
        prompt=body.prompt,
        template_id=body.template_id,
        duration_target_sec=body.duration_target_sec,
        content_source=body.content_source,
        idempotency_key=idem,
        created_at=now,
        updated_at=now,
        metadata=body.metadata,
    )
    store.save(job)
    celery.send_task("worker.process_job", args=[job_id])
    return _job_to_response(job)


@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str) -> JobResponse:
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_response(job)


@app.get("/artifacts/{artifact_id}", response_model=ArtifactResponse)
def get_artifact(artifact_id: str) -> ArtifactResponse:
    job = store.get(artifact_id)
    if not job or not job.artifact_key:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return ArtifactResponse(
        id=artifact_id,
        job_id=job.id,
        bytes=job.artifact_bytes,
        download_url=storage.presigned_get(job.artifact_key),
    )
