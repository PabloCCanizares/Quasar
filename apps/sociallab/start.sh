#!/bin/bash
# ============================================================
# SocialLab — Script de arranque
# ============================================================
# Uso:
#   ./start.sh          → Arranca la web (FastAPI)
#   ./start.sh seed     → Genera datos sucios en data/raw/
#   ./start.sh etl      → Ejecuta Spark ETL (raw→silver→gold)
#   ./start.sh load     → Carga silver/gold a MongoDB y Neo4j
#   ./start.sh all      → seed + etl + load + web
#   ./start.sh reset    → Borra datos, regenera todo y arranca
# ============================================================

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

# Java 17 para Spark
export JAVA_HOME="/opt/homebrew/Cellar/openjdk@17/17.0.17/libexec/openjdk.jdk/Contents/Home"

# Activar venv
source .venv/bin/activate

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[SocialLab]${NC} $1"; }
ok()  { echo -e "${GREEN}[✓]${NC} $1"; }

cmd="${1:-web}"

case "$cmd" in

    web)
        log "Arrancando FastAPI en http://localhost:8000"
        python main.py
        ;;

    seed)
        log "Generando datos sucios en data/raw/"
        python -m src.seed.generate_dirty_data
        ok "Datos generados"
        ;;

    etl)
        log "Ejecutando Spark ETL (raw → silver → gold)"
        python -m src.spark.run_pipeline
        ok "ETL completado"
        ;;

    load)
        log "Cargando datos a MongoDB y Neo4j via Spark"
        python -m src.spark.run_pipeline --mongo --neo4j
        ok "Datos cargados"
        ;;

    load-mongo)
        log "Cargando datos a MongoDB via Spark"
        python -m src.spark.run_pipeline --mongo
        ok "MongoDB cargado"
        ;;

    load-neo4j)
        log "Cargando datos a Neo4j via Spark"
        python -m src.spark.run_pipeline --neo4j
        ok "Neo4j cargado"
        ;;

    all)
        $0 seed
        $0 etl
        $0 load-mongo
        $0 web
        ;;

    reset)
        log "Borrando datos existentes..."
        rm -rf data/raw/*.json data/silver/* data/gold/*
        python -c "
from src.web.database import get_sync_db
db = get_sync_db()
for c in db.list_collection_names():
    db[c].drop()
print('MongoDB limpio')
"
        ok "Datos borrados"
        $0 all
        ;;

    *)
        echo "Uso: ./start.sh [web|seed|etl|load|load-mongo|load-neo4j|all|reset]"
        exit 1
        ;;
esac
