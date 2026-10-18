FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SENTINELA_DATABASE_PATH=/app/data/sentinela.db
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir . \
    && mkdir -p /app/data \
    && useradd --system --uid 10001 --create-home sentinela \
    && chown -R sentinela:sentinela /app
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "sentinela.main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
