import tempfile
from pathlib import Path

from app.celery_app import celery_app
from app.pipeline.render import render_short
from app.pipeline.script import generate_script
from app.pipeline.tts import synthesize_scenes
from storytime_common.models import JobRecord, JobStatus
from storytime_common.redis_store import JobStore
from storytime_common.settings import Settings
from storytime_common.storage import ObjectStorage


def _set_status(store: JobStore, job: JobRecord, status: JobStatus) -> JobRecord:
    job.status = status
    job.updated_at = JobRecord.now()
    store.update(job)
    return job


@celery_app.task(name="worker.process_job")
def process_job(job_id: str) -> str:
    settings = Settings()
    store = JobStore(settings)
    storage = ObjectStorage(settings)

    job = store.get(job_id)
    if not job:
        return "missing"

    try:
        job = _set_status(store, job, JobStatus.scripting)
        script = generate_script(
            job.prompt,
            job.template_id,
            job.duration_target_sec,
            job.content_source,
        )
        job.script = script
        store.update(job)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            job = _set_status(store, job, JobStatus.tts)
            scene_wavs = synthesize_scenes(script["scenes"], tmp_path)
            job.script = script
            store.update(job)

            job = _set_status(store, job, JobStatus.rendering)
            mp4 = tmp_path / "output.mp4"
            render_short(script, scene_wavs, mp4)

            job = _set_status(store, job, JobStatus.uploading)
            key = f"jobs/{job.id}/v1/output.mp4"
            size = storage.upload_file(str(mp4), key)
            job.artifact_key = key
            job.artifact_bytes = size
            job = _set_status(store, job, JobStatus.done)
        return job_id
    except Exception as exc:  # noqa: BLE001 — worker boundary; persist failure on job record
        job.status = JobStatus.failed
        job.error = str(exc)
        job.updated_at = JobRecord.now()
        store.update(job)
        raise
