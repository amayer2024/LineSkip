# syntax=docker/dockerfile:1
# LineSkip — analytics service (events table; ingest + revenue reports).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py config.py db.py repository.py service.py ./
COPY migrations/ ./migrations/

RUN useradd --system --no-create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["python", "app.py"]
