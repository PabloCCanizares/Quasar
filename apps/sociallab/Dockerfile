# SocialLab — imagen para FastAPI + PySpark dentro del ecosistema Quasar.
#
# El build context es la RAÍZ del repo (Quasar/), no apps/sociallab/.
# Esto permite copiar tanto apps/sociallab/ como infra/shared/ en una sola
# imagen sin contorsiones de ruta.

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
COPY apps/sociallab/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Infraestructura compartida (libs comunes a todas las apps de Quasar)
COPY infra/shared /app/infra/shared

# Código de la app
COPY apps/sociallab/main.py /app/
COPY apps/sociallab/src /app/src

EXPOSE 8000

CMD ["python", "main.py"]
