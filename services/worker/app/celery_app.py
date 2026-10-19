from celery import Celery

from storytime_common.settings import Settings

settings = Settings()

celery_app = Celery(
    "storytime",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks"],
)

celery_app.conf.task_routes = {"app.tasks.*": {"queue": "celery"}}
