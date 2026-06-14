# Quasar Hub — app central ligera (sin Spark/Java).
# Build context = raíz del repo (Quasar/).

FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY apps/hub/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY infra/shared /app/infra/shared
COPY apps/hub/main.py /app/
COPY apps/hub/src /app/src

EXPOSE 8080

CMD ["python", "main.py"]
