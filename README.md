# GymRAG
Chatbot RAG tiếng Việt về gym & dinh dưỡng, kèm trích dẫn nguồn.
Trọng tâm: pipeline LLMOps kiểm soát chất lượng (eval, quality gate, CI/CD, monitoring).

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
