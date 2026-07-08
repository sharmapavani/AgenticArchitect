# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-docker.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --default-timeout=300 --retries 5 -r requirements-docker.txt

COPY pyproject.toml README.md ./
COPY src ./src
COPY scripts ./scripts
COPY knowledge ./knowledge

RUN pip install --no-deps -e .

COPY docker/entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

ENV API_HOST=0.0.0.0
ENV API_PORT=8000
ENV CHROMA_PATH=.chroma
ENV CHAT_AUDIT_DB_PATH=./data/chat_audit.db

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["serve"]
