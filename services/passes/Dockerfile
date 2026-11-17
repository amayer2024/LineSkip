# syntax=docker/dockerfile:1
# LineSkip — passes service (auth + passes domains, JSON API).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py config.py db.py analytics_client.py ./
COPY migrations/ ./migrations/
COPY auth/ ./auth/
COPY passes/ ./passes/

RUN useradd --system --no-create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["python", "app.py"]
