FROM python:3.12-slim

WORKDIR /app

COPY packages/storytime_common /app/packages/storytime_common
COPY services/api/requirements.txt /app/services/api/requirements.txt
RUN pip install --no-cache-dir -r /app/services/api/requirements.txt

COPY services/api/app /app/services/api/app
COPY schemas /app/schemas
COPY templates /app/templates

ENV PYTHONPATH=/app/services/api:/app/packages/storytime_common
WORKDIR /app/services/api

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
