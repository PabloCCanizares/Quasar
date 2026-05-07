#!/usr/bin/env bash
# ==========================================================
# SocialLab — laboratorio en Docker
#
# Permite arrancar el ecosistema completo y "destapar" bloques
# de ejercicios (Cypher de Neo4j y modelos ML) sin tocar codigo.
#
# Uso: ./lab.sh <comando> [args]
# ==========================================================

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

ENV_FILE=".env.docker"
COMPOSE=()

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${BLUE}[lab]${NC} $1"; }
ok()   { echo -e "${GREEN}[OK]${NC}  $1"; }
warn() { echo -e "${YELLOW}[!]${NC}  $1"; }
err()  { echo -e "${RED}[ERR]${NC} $1" >&2; }

ensure_docker() {
    if ! command -v docker > /dev/null 2>&1; then
        err "docker no esta instalado o no esta en PATH"
        echo "  Instala Docker Desktop: https://www.docker.com/products/docker-desktop"
        exit 1
    fi

    if docker compose version > /dev/null 2>&1; then
        COMPOSE=(docker compose)
    elif command -v docker-compose > /dev/null 2>&1; then
        COMPOSE=(docker-compose)
    else
        err "Docker Compose no esta disponible"
        echo "  Instala/actualiza Docker Desktop, o instala el binario legacy 'docker-compose'."
        exit 1
    fi
}

# ----------------------------------------------------------
# Edicion del flag en .env.docker
#   var    : LAB_NEO4J | LAB_ML
#   action : unlock | lock | all | none
#   block  : basic | intermediate | advanced | supervised | ...
# Devuelve por stdout el nuevo valor.
# ----------------------------------------------------------
update_flag() {
    local var="$1" action="$2" block="$3"
    python3 - "$var" "$action" "$block" "$ENV_FILE" <<'PYEOF'
import re, sys

var, action, block, env_file = sys.argv[1:5]

NEO4J_BLOCKS = {"basic", "intermediate", "advanced"}
ML_BLOCKS = {"supervised", "unsupervised", "graph_ml"}
ALL = NEO4J_BLOCKS if var == "LAB_NEO4J" else ML_BLOCKS

with open(env_file) as f:
    content = f.read()

m = re.search(rf'^{var}=(.*)$', content, re.MULTILINE)
current = m.group(1).strip() if m else ""

if current == "all":
    blocks = set(ALL)
else:
    blocks = {b.strip() for b in current.split(",") if b.strip()}

if action == "unlock":
    if block not in ALL:
        sys.stderr.write(f"Bloque desconocido: {block}. Validos: {sorted(ALL)}\n")
        sys.exit(2)
    blocks.add(block)
elif action == "lock":
    blocks.discard(block)
elif action == "all":
    blocks = set(ALL)
elif action == "none":
    blocks = set()
else:
    sys.stderr.write(f"Action desconocida: {action}\n")
    sys.exit(2)

new_value = ",".join(sorted(blocks))
content = re.sub(rf'^{var}=.*$', f'{var}={new_value}', content, flags=re.MULTILINE)

with open(env_file, "w") as f:
    f.write(content)

print(new_value if new_value else "(empty)")
PYEOF
}

restart_app() {
    log "Recreando el contenedor 'app' para recoger nuevos flags..."
    "${COMPOSE[@]}" up -d app
    ok "Listo. Recarga el navegador."
}

train_ml_artifacts() {
    clear_ml_artifacts
    log "Entrenando modelos ML segun LAB_ML actual..."
    "${COMPOSE[@]}" exec app python -m src.spark.models.run_all
    ok "Modelos ML actualizados. Recarga la vista Spark/ML."
}

clear_ml_artifacts() {
    if [[ -d data/gold/models ]]; then
        log "Limpiando modelos ML generados previamente (data/gold/models)..."
        rm -rf data/gold/models
    fi
}

ensure_raw_data() {
    local missing=0
    for file in users posts likes follows; do
        if [[ ! -s "data/raw/${file}.json" ]]; then
            missing=1
        fi
    done

    if [[ "$missing" -eq 1 ]]; then
        warn "No encuentro data/raw/{users,posts,likes,follows}.json."
        log "Generando datos raw automaticamente antes del ETL..."
        "${COMPOSE[@]}" exec app python -m src.seed.generate_dirty_data
    fi
}

cmd="${1:-help}"

case "$cmd" in

    # --------------------------------------------------------
    # Ciclo de vida
    # --------------------------------------------------------
    up)
        ensure_docker
        mode="${2:-}"
        if [[ -n "$mode" ]]; then
            case "$mode" in
                exercises)
                    update_flag LAB_NEO4J none "" > /dev/null
                    update_flag LAB_ML none "" > /dev/null
                    log "Modo: ejercicios (todos los algoritmos como scaffold)"
                    ;;
                solutions|all)
                    update_flag LAB_NEO4J all "" > /dev/null
                    update_flag LAB_ML all "" > /dev/null
                    log "Modo: soluciones (todos los algoritmos resueltos)"
                    ;;
                *)
                    err "Modo desconocido: $mode"
                    echo "  Modos validos: exercises | solutions"
                    exit 1
                    ;;
            esac
        else
            log "Arrancando con la configuracion actual de $ENV_FILE"
        fi
        "${COMPOSE[@]}" up -d --build
        ok "Web:  http://localhost:8000"
        ok "Neo4j browser: http://localhost:7474  (neo4j / neo4jneo4j)"
        ;;

    down)
        ensure_docker
        log "Parando contenedores (volumenes preservados)..."
        "${COMPOSE[@]}" down
        ;;

    cloud)
        if [[ ! -f .env.cloud ]]; then
            err "Falta .env.cloud. Copia la plantilla y rellena las URIs:"
            echo "  cp .env.cloud.example .env.cloud"
            echo "  # rellena MONGO_URI, NEO4J_URI, NEO4J_PASSWORD con tus credenciales"
            echo
            echo "Guia paso a paso: docs/MIGRACION_CLOUD.md"
            echo
            echo "Alternativa sin Docker (alumno muy ligero):"
            echo "  cp .env.cloud .env && python main.py   # usa el venv local"
            exit 1
        fi
        ensure_docker
        # Si el modo local esta corriendo, los puertos chocan (8000)
        if "${COMPOSE[@]}" ps --status running --quiet 2>/dev/null | grep -q .; then
            log "Modo local detectado — parandolo primero (mongo/neo4j locales se quedan)..."
            "${COMPOSE[@]}" stop
        fi
        log "Arrancando solo el contenedor 'app' apuntando a Atlas/Aura..."
        "${COMPOSE[@]}" -f docker-compose.cloud.yml up -d --build
        ok "Web: http://localhost:8000"
        ok "Mongo y Neo4j viven en cloud — no hay contenedores locales para esas BBDD"
        ;;

    cloud-down)
        ensure_docker
        log "Parando contenedor cloud..."
        "${COMPOSE[@]}" -f docker-compose.cloud.yml down
        ;;

    reset)
        ensure_docker
        warn "Esto borrara TODOS los datos:"
        warn "  - volumenes Docker (mongo_data, neo4j_data, neo4j_logs, spark_ivy)"
        warn "  - contenido de data/{raw,silver,gold}/"
        read -r -p "Escribe 'yes' para continuar: " ans
        if [[ "$ans" != "yes" ]]; then
            log "Cancelado"
            exit 0
        fi
        "${COMPOSE[@]}" down -v
        rm -rf data/raw/*.json data/silver/* data/gold/* 2>/dev/null || true
        ok "Estado limpio. Arranca con: ./lab.sh up"
        ;;

    # --------------------------------------------------------
    # Modo laboratorio
    # --------------------------------------------------------
    unlock)
        kind="${2:-}"; block="${3:-}"
        if [[ -z "$kind" || -z "$block" ]]; then
            err "Uso: ./lab.sh unlock {neo4j|ml} <bloque>"
            echo "  neo4j: basic | intermediate | advanced"
            echo "  ml:    supervised | unsupervised | graph_ml"
            exit 1
        fi
        case "$kind" in
            neo4j) new=$(update_flag LAB_NEO4J unlock "$block"); ok "LAB_NEO4J = $new" ;;
            ml)    new=$(update_flag LAB_ML    unlock "$block"); ok "LAB_ML    = $new" ;;
            *)     err "kind debe ser 'neo4j' o 'ml'"; exit 1 ;;
        esac
        ensure_docker
        restart_app
        if [[ "$kind" == "ml" ]]; then
            train_ml_artifacts
        fi
        ;;

    lock)
        kind="${2:-}"; block="${3:-}"
        if [[ -z "$kind" || -z "$block" ]]; then
            err "Uso: ./lab.sh lock {neo4j|ml} <bloque>"
            exit 1
        fi
        case "$kind" in
            neo4j) new=$(update_flag LAB_NEO4J lock "$block"); ok "LAB_NEO4J = $new" ;;
            ml)    new=$(update_flag LAB_ML    lock "$block"); ok "LAB_ML    = $new"; clear_ml_artifacts ;;
            *)     err "kind debe ser 'neo4j' o 'ml'"; exit 1 ;;
        esac
        ensure_docker
        restart_app
        ;;

    solutions)
        update_flag LAB_NEO4J all "" > /dev/null
        update_flag LAB_ML all "" > /dev/null
        ok "Todo desbloqueado: LAB_NEO4J=all, LAB_ML=all"
        ensure_docker
        restart_app
        train_ml_artifacts
        ;;

    exercises)
        update_flag LAB_NEO4J none "" > /dev/null
        update_flag LAB_ML none "" > /dev/null
        clear_ml_artifacts
        ok "Todo en modo ejercicio (scaffold)"
        ensure_docker
        restart_app
        ;;

    status)
        echo
        log "Estado de los flags ($ENV_FILE):"
        grep -E '^LAB_NEO4J=|^LAB_ML=' "$ENV_FILE" | sed 's/^/    /'
        echo
        if command -v docker > /dev/null 2>&1; then
            log "Servicios Docker:"
            ensure_docker
            "${COMPOSE[@]}" ps 2>/dev/null | sed 's/^/    /' || warn "Compose no esta corriendo"
        fi
        echo
        ;;

    # --------------------------------------------------------
    # Pipeline de datos (dentro del contenedor app)
    # --------------------------------------------------------
    seed)
        ensure_docker
        clear_ml_artifacts
        log "Generando datos sucios en data/raw/..."
        "${COMPOSE[@]}" exec app python -m src.seed.generate_dirty_data
        ;;

    etl)
        ensure_docker
        clear_ml_artifacts
        ensure_raw_data
        log "Ejecutando Spark ETL completo (raw -> silver -> gold + carga Mongo/Neo4j)..."
        "${COMPOSE[@]}" exec app python -m src.spark.run_pipeline --all
        ;;

    train)
        ensure_docker
        train_ml_artifacts
        ;;

    logs)
        ensure_docker
        svc="${2:-}"
        if [[ -n "$svc" ]]; then
            "${COMPOSE[@]}" logs -f "$svc"
        else
            "${COMPOSE[@]}" logs -f
        fi
        ;;

    # --------------------------------------------------------
    # Ayuda
    # --------------------------------------------------------
    help|--help|-h|*)
        cat <<'USAGE'
SocialLab — laboratorio en Docker

Uso: ./lab.sh <comando> [args]

Ciclo de vida (modo local — todo en Docker):
    up [exercises|solutions]    Arranca el ecosistema completo (mongo+neo4j+app).
                                Sin argumento usa lo que haya en .env.docker.
    down                         Para los contenedores. Datos preservados.
    reset                        Borra volumenes y data/{raw,silver,gold} (pide confirmacion).
    status                       Muestra los flags actuales y estado de los servicios.

Ciclo de vida (modo cloud — Atlas + Aura, free tier):
    cloud                        Arranca SOLO el contenedor 'app' apuntando a las BBDD
                                cloud definidas en .env.cloud. Requiere haberlo creado
                                con: cp .env.cloud.example .env.cloud (y rellenar URIs).
                                Guia: docs/MIGRACION_CLOUD.md
    cloud-down                   Para el contenedor cloud.

Modo laboratorio:
    unlock {neo4j|ml} <bloque>  Marca un bloque como resuelto y reinicia el contenedor app.
    lock   {neo4j|ml} <bloque>  Vuelve a esconderlo (scaffold) y reinicia.
    solutions                    Desbloquea todo (atajo: LAB_NEO4J=all, LAB_ML=all).
    exercises                    Bloquea todo (todos los algoritmos como scaffold).

  Bloques Neo4j: basic | intermediate | advanced
  Bloques ML:    supervised | unsupervised | graph_ml

Pipeline de datos (se ejecuta dentro del contenedor app):
    seed                         Genera datos sucios en data/raw/.
    etl                          Spark: raw -> silver -> gold + carga MongoDB y Neo4j.
    train                        Entrena los modelos ML del LAB_ML actual.

Otros:
    logs [servicio]              Sigue logs (de todos o de mongodb|neo4j|app).
    help                         Esta ayuda.

Flujo tipico (primer arranque, alumno):
    ./lab.sh up exercises        # ecosistema en scaffold
    ./lab.sh seed                # genera raw data
    ./lab.sh etl                 # carga la red social en Mongo+Neo4j
    # ... el alumno trabaja sobre los archivos *_ex.py ...

Flujo tipico (profesor en clase, va destapando):
    ./lab.sh unlock neo4j basic           # tras la clase de Cypher basico
    ./lab.sh unlock ml supervised         # tras la clase de clasificacion
    ./lab.sh status                       # comprobar que se desbloqueo

Flujo tipico (alumno con poco ordenador — modo cloud free):
    cp .env.cloud.example .env.cloud      # plantilla
    # editar .env.cloud con URIs de Atlas / Aura del profesor
    ./lab.sh cloud                        # ~150 MB RAM, sin mongo/neo4j locales

Web (ambos modos):    http://localhost:8000
Neo4j browser (local): http://localhost:7474   (neo4j / neo4jneo4j)
USAGE
        ;;
esac
