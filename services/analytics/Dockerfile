# syntax=docker/dockerfile:1
# LineSkip — analytics service (owns the events table; ingest + revenue reports).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    DATA_DIR=/data

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py config.py db.py schema.sql repository.py service.py ./

RUN useradd --system --no-create-home appuser \
 && mkdir -p /data \
 && chown -R appuser:appuser /data /app
USER appuser

EXPOSE 8000
CMD ["python", "app.py"]
