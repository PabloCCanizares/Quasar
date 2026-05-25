#!/usr/bin/env bash
# ==========================================================
# Quasar — orquestador del ecosistema (Big Data + IA).
#
# Apps del ecosistema:
#   sociallab    Red social poliglota (Twitter + MongoDB + Neo4j + Spark ML)
#   preprolab    Preprocesamiento clasico del Tema 5 — proximamente
#   llmprep      Limpieza de corpus + nanoGPT — proximamente
#
# Sintaxis general:
#   ./lab.sh <app> <comando> [args]
#
# Ejemplos:
#   ./lab.sh sociallab up exercises
#   ./lab.sh sociallab seed
#   ./lab.sh sociallab etl
#   ./lab.sh sociallab unlock neo4j basic
#   ./lab.sh help
# ==========================================================

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

COMPOSE_DIR="$DIR/infra/compose"
COMPOSE_FILE="$COMPOSE_DIR/docker-compose.yml"
COMPOSE_CLOUD_FILE="$COMPOSE_DIR/docker-compose.cloud.yml"
ENV_FILE="$COMPOSE_DIR/.env.docker"

COMPOSE=()

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${BLUE}[quasar]${NC} $1"; }
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

# Atajo: ejecuta docker compose con el archivo y env_file correctos.
compose() {
    "${COMPOSE[@]}" -f "$COMPOSE_FILE" --env-file "$ENV_FILE" "$@"
}

compose_cloud() {
    "${COMPOSE[@]}" -f "$COMPOSE_CLOUD_FILE" "$@"
}

# ----------------------------------------------------------
# Edicion del flag en .env.docker
#   var    : LAB_NEO4J | LAB_ML
#   action : unlock | lock | all | none
#   block  : basic | intermediate | advanced | supervised | ...
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

# ==========================================================
# SocialLab
# ==========================================================

SOCIALLAB_SERVICE="app-sociallab"
SOCIALLAB_DATA="$DIR/infra/data/sociallab"

sociallab_restart_app() {
    log "Recreando el contenedor '$SOCIALLAB_SERVICE' para recoger nuevos flags..."
    compose up -d "$SOCIALLAB_SERVICE"
    ok "Listo. Recarga el navegador."
}

sociallab_clear_ml_artifacts() {
    if [[ -d "$SOCIALLAB_DATA/gold/models" ]]; then
        log "Limpiando modelos ML generados previamente (infra/data/sociallab/gold/models)..."
        rm -rf "$SOCIALLAB_DATA/gold/models"
    fi
}

sociallab_train_ml_artifacts() {
    sociallab_clear_ml_artifacts
    log "Entrenando modelos ML segun LAB_ML actual..."
    compose exec "$SOCIALLAB_SERVICE" python -m src.spark.models.run_all
    ok "Modelos ML actualizados. Recarga la vista Spark/ML."
}

sociallab_ensure_raw_data() {
    local missing=0
    for file in users posts likes follows; do
        if [[ ! -s "$SOCIALLAB_DATA/raw/${file}.json" ]]; then
            missing=1
        fi
    done

    if [[ "$missing" -eq 1 ]]; then
        warn "No encuentro infra/data/sociallab/raw/{users,posts,likes,follows}.json."
        log "Generando datos raw automaticamente antes del ETL..."
        compose exec "$SOCIALLAB_SERVICE" python -m src.seed.generate_dirty_data
    fi
}

sociallab_usage() {
    cat <<EOF
SocialLab — comandos disponibles

Ciclo de vida (modo Docker local):
    up [exercises|solutions]    Arranca mongo + neo4j + app-sociallab.
    down                         Para los contenedores. Datos preservados.
    status                       Muestra los flags actuales y el estado.
    reset                        Borra volumenes y data/{raw,silver,gold} (pide confirmacion).
    logs [servicio]              Sigue logs (de todos o de mongodb|neo4j|app-sociallab).

Ciclo de vida (modo cloud — Atlas + Aura free tier):
    cloud                        Arranca solo el contenedor app contra cloud.
                                Requiere apps/sociallab/.env.cloud relleno.
    cloud-down                   Para el contenedor cloud.

Modo laboratorio (flags en infra/compose/.env.docker):
    unlock {neo4j|ml} <bloque>  Marca un bloque como resuelto y reinicia.
    lock   {neo4j|ml} <bloque>  Vuelve a esconderlo (scaffold) y reinicia.
    solutions                    Desbloquea todo.
    exercises                    Bloquea todo (scaffold).
  Bloques Neo4j: basic | intermediate | advanced
  Bloques ML:    supervised | unsupervised | graph_ml

Pipeline de datos:
    seed                         Genera datos sucios en infra/data/sociallab/raw/.
    etl                          Spark: raw -> silver -> gold + carga MongoDB y Neo4j.
    train                        Entrena los modelos ML del LAB_ML actual.

Ejemplos:
    ./lab.sh sociallab up exercises
    ./lab.sh sociallab seed
    ./lab.sh sociallab etl
    ./lab.sh sociallab unlock neo4j basic
    ./lab.sh sociallab unlock ml supervised
    ./lab.sh sociallab status

Web SocialLab:  http://localhost:8000
Neo4j browser:   http://localhost:7474   (neo4j / neo4jneo4j)
EOF
}

sociallab_cmd() {
    local cmd="${1:-help}"
    shift || true

    case "$cmd" in

        # ---- Ciclo de vida ----
        up)
            ensure_docker
            mode="${1:-}"
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
            compose up -d --build
            ok "Web:  http://localhost:8000"
            ok "Neo4j browser: http://localhost:7474  (neo4j / neo4jneo4j)"
            ;;

        down)
            ensure_docker
            log "Parando contenedores (volumenes preservados)..."
            compose down
            ;;

        cloud)
            local cloud_env="$DIR/apps/sociallab/.env.cloud"
            if [[ ! -f "$cloud_env" ]]; then
                err "Falta apps/sociallab/.env.cloud. Copia la plantilla y rellena las URIs:"
                echo "  cp apps/sociallab/.env.cloud.example apps/sociallab/.env.cloud"
                echo "  # rellena MONGO_URI, NEO4J_URI, NEO4J_PASSWORD con tus credenciales"
                echo
                echo "Guia paso a paso: docs/MIGRACION_CLOUD.md"
                exit 1
            fi
            ensure_docker
            # Si el modo local esta corriendo, los puertos chocan (8000).
            if compose ps --status running --quiet 2>/dev/null | grep -q .; then
                log "Modo local detectado — parandolo primero (mongo/neo4j locales se quedan)..."
                compose stop
            fi
            log "Arrancando solo el contenedor cloud apuntando a Atlas/Aura..."
            compose_cloud up -d --build
            ok "Web: http://localhost:8000"
            ok "Mongo y Neo4j viven en cloud — no hay contenedores locales para esas BBDD"
            ;;

        cloud-down)
            ensure_docker
            log "Parando contenedor cloud..."
            compose_cloud down
            ;;

        reset)
            ensure_docker
            warn "Esto borrara TODOS los datos de SocialLab:"
            warn "  - volumenes Docker (mongo_data, neo4j_data, neo4j_logs, spark_ivy)"
            warn "  - contenido de infra/data/sociallab/{raw,silver,gold}/"
            read -r -p "Escribe 'yes' para continuar: " ans
            if [[ "$ans" != "yes" ]]; then
                log "Cancelado"
                exit 0
            fi
            compose down -v
            rm -rf "$SOCIALLAB_DATA"/raw/*.json "$SOCIALLAB_DATA"/silver/* "$SOCIALLAB_DATA"/gold/* 2>/dev/null || true
            ok "Estado limpio. Arranca con: ./lab.sh sociallab up"
            ;;

        # ---- Modo laboratorio ----
        unlock)
            local kind="${1:-}" block="${2:-}"
            if [[ -z "$kind" || -z "$block" ]]; then
                err "Uso: ./lab.sh sociallab unlock {neo4j|ml} <bloque>"
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
            sociallab_restart_app
            if [[ "$kind" == "ml" ]]; then
                sociallab_train_ml_artifacts
            fi
            ;;

        lock)
            local kind="${1:-}" block="${2:-}"
            if [[ -z "$kind" || -z "$block" ]]; then
                err "Uso: ./lab.sh sociallab lock {neo4j|ml} <bloque>"
                exit 1
            fi
            case "$kind" in
                neo4j) new=$(update_flag LAB_NEO4J lock "$block"); ok "LAB_NEO4J = $new" ;;
                ml)    new=$(update_flag LAB_ML    lock "$block"); ok "LAB_ML    = $new"; sociallab_clear_ml_artifacts ;;
                *)     err "kind debe ser 'neo4j' o 'ml'"; exit 1 ;;
            esac
            ensure_docker
            sociallab_restart_app
            ;;

        solutions)
            update_flag LAB_NEO4J all "" > /dev/null
            update_flag LAB_ML all "" > /dev/null
            ok "Todo desbloqueado: LAB_NEO4J=all, LAB_ML=all"
            ensure_docker
            sociallab_restart_app
            sociallab_train_ml_artifacts
            ;;

        exercises)
            update_flag LAB_NEO4J none "" > /dev/null
            update_flag LAB_ML none "" > /dev/null
            sociallab_clear_ml_artifacts
            ok "Todo en modo ejercicio (scaffold)"
            ensure_docker
            sociallab_restart_app
            ;;

        status)
            echo
            log "Estado de los flags ($ENV_FILE):"
            grep -E '^LAB_NEO4J=|^LAB_ML=' "$ENV_FILE" | sed 's/^/    /'
            echo
            if command -v docker > /dev/null 2>&1; then
                log "Servicios Docker (Quasar):"
                ensure_docker
                compose ps 2>/dev/null | sed 's/^/    /' || warn "Compose no esta corriendo"
            fi
            echo
            ;;

        # ---- Pipeline de datos ----
        seed)
            ensure_docker
            sociallab_clear_ml_artifacts
            log "Generando datos sucios en infra/data/sociallab/raw/..."
            compose exec "$SOCIALLAB_SERVICE" python -m src.seed.generate_dirty_data
            ;;

        etl)
            ensure_docker
            sociallab_clear_ml_artifacts
            sociallab_ensure_raw_data
            log "Ejecutando Spark ETL completo (raw -> silver -> gold + carga Mongo/Neo4j)..."
            compose exec "$SOCIALLAB_SERVICE" python -m src.spark.run_pipeline --all
            ;;

        train)
            ensure_docker
            sociallab_train_ml_artifacts
            ;;

        logs)
            ensure_docker
            local svc="${1:-}"
            if [[ -n "$svc" ]]; then
                compose logs -f "$svc"
            else
                compose logs -f
            fi
            ;;

        help|--help|-h|"")
            sociallab_usage
            ;;

        *)
            err "Comando desconocido: $cmd"
            sociallab_usage
            exit 1
            ;;
    esac
}

# ==========================================================
# Top-level routing
# ==========================================================

quasar_usage() {
    cat <<EOF
Quasar — laboratorio Big Data + IA (multi-app).

Uso:    ./lab.sh <app> <comando> [args]

Apps disponibles:
    sociallab    Red social poliglota (Twitter + MongoDB + Neo4j + Spark ML)
                 33 ejercicios distribuidos en 3 bloques Cypher + 3 bloques ML.

Apps planificadas (proximamente):
    preprolab    Preprocesamiento clasico del Tema 5 (Fase posterior).
    llmprep      Limpieza de corpus + nanoGPT (Fase posterior).

Comandos comunes (varian por app):
    up [exercises|solutions]    Arranca la app
    down                        Para los contenedores
    seed                        Genera datos
    etl                         Ejecuta el pipeline ETL
    train                       Entrena modelos ML
    status                      Estado actual
    unlock / lock <kind> <bloque>  Gestiona ejercicios
    reset                       Borra todos los datos

Ayuda especifica:
    ./lab.sh sociallab help

Ejemplos:
    ./lab.sh sociallab up exercises
    ./lab.sh sociallab seed
    ./lab.sh sociallab etl
    ./lab.sh sociallab unlock neo4j basic
EOF
}

app="${1:-help}"
shift || true

case "$app" in
    sociallab)
        sociallab_cmd "$@"
        ;;
    preprolab|llmprep)
        warn "La app '$app' aun no esta implementada."
        echo "  Esta planificada para una fase posterior del roadmap de Quasar."
        echo "  Por ahora solo 'sociallab' esta operativa."
        exit 1
        ;;
    help|--help|-h|"")
        quasar_usage
        ;;
    *)
        err "App desconocida: $app"
        quasar_usage
        exit 1
        ;;
esac
