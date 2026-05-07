# SocialLab — imagen para FastAPI + PySpark.
# El setup nativo (start.sh) sigue siendo el principal; esto es un añadido.

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

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py ./
COPY src ./src

EXPOSE 8000

CMD ["python", "main.py"]
