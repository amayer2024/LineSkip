# syntax=docker/dockerfile:1
# LineSkip — passes service (auth + passes domains + web UI).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    DATA_DIR=/data

WORKDIR /app

# Dependencies first so a code edit does not reinstall packages.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Only the application code, listed explicitly (never COPY . .).
COPY app.py config.py db.py schema.sql ./
COPY auth/ ./auth/
COPY passes/ ./passes/
COPY analytics/ ./analytics/
COPY templates/ ./templates/
COPY static/ ./static/

# Non-root user; /data is where the SQLite file lives (mountable volume).
RUN useradd --system --no-create-home appuser \
 && mkdir -p /data \
 && chown -R appuser:appuser /data /app
USER appuser

EXPOSE 8000
CMD ["python", "app.py"]
