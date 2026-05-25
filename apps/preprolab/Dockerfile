# PreproLab — imagen para FastAPI + PySpark dentro del ecosistema Quasar.
#
# El build context es la RAÍZ del repo (Quasar/), no apps/preprolab/.
# Permite copiar tanto apps/preprolab/ como infra/shared/ en una sola imagen.

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

# Dependencias Python de la app
COPY apps/preprolab/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Infraestructura compartida
COPY infra/shared /app/infra/shared

# Código de la app
COPY apps/preprolab/main.py /app/
COPY apps/preprolab/src /app/src

EXPOSE 8002

CMD ["python", "main.py"]
