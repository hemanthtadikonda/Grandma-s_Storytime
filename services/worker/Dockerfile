FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg fonts-quicksand \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY packages/storytime_common /app/packages/storytime_common
COPY services/worker/requirements.txt /app/services/worker/requirements.txt
RUN pip install --no-cache-dir /app/packages/storytime_common \
    && pip install --no-cache-dir -r /app/services/worker/requirements.txt

COPY services/worker/app /app/services/worker/app
COPY schemas /app/schemas
COPY templates /app/templates

ENV PYTHONPATH=/app/services/worker:/app/packages/storytime_common
WORKDIR /app/services/worker

CMD ["celery", "-A", "app.celery_app", "worker", "--loglevel=INFO", "-Q", "celery"]
