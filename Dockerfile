FROM python:3.13-slim

WORKDIR /app

RUN pip install --no-cache-dir quilmem[mcp]

ENTRYPOINT ["agentmem", "--db", "/data/memory.db", "--project", "default", "serve"]
