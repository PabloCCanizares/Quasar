# LLM Lab — imagen FastAPI + PySpark dentro del ecosistema Quasar.
# Build context = raíz del repo (Quasar/).

FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
        openjdk-17-jre-headless \
        procps \
        curl \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /usr/lib/jvm/java-17-openjdk-* /usr/lib/jvm/default

ENV JAVA_HOME=/usr/lib/jvm/default \
    PATH="/usr/lib/jvm/default/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY apps/llmprep/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY infra/shared /app/infra/shared
COPY apps/llmprep/main.py /app/
COPY apps/llmprep/src /app/src

EXPOSE 8001

CMD ["python", "main.py"]
