# GymRAG
Chatbot RAG tiếng Việt về gym & dinh dưỡng, kèm trích dẫn nguồn.
Trọng tâm: pipeline LLMOps kiểm soát chất lượng (eval, quality gate, CI/CD, monitoring). 

[![CI](https://github.com/QuocKhanhDev-it/GymRAG/actions/workflows/ci.yml/badge.svg)](https://github.com/QuocKhanhDev-it/GymRAG/actions/workflows/ci.yml)

## Chạy thử
1. `cp .env.example .env` rồi điền API key
2. (sẽ bổ sung dần)

## Run with Docker

```bash
cp .env.example .env   # then fill in your values
docker compose up -d --build
curl -s localhost:8000/health
```

API docs: http://localhost:8000/docs 

## Development

```bash
uv pip install -r requirements-dev.txt
ruff check . && ruff format --check .
pytest -q
```

Tests use a fake LLM, so they need no API key and no network access.
CI runs the same checks plus a Docker build on every pull request.
