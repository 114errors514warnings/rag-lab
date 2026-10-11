# rag-lab · 知识引擎服务（阶段七）
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY rag_engine ./rag_engine
COPY rag_eval ./rag_eval
COPY service ./service
COPY data ./data
COPY baselines ./baselines
COPY scripts ./scripts

RUN mkdir -p /app/reports /app/data/index
VOLUME ["/app/data", "/app/reports"]

EXPOSE 8099

CMD ["python", "-m", "uvicorn", "service.api:app", "--host", "0.0.0.0", "--port", "8099"]
