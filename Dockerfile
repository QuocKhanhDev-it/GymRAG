# Small official Python image, same version as local dev
FROM python:3.12-slim

# No .pyc files; flush logs immediately so `docker logs` shows them
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first: this layer is cached until requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code last: it changes most often
COPY config.yaml .
COPY prompts/ prompts/
COPY app/ app/

# Run as a non-root user
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]