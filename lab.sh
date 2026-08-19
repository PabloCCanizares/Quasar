#!/usr/bin/env bash
# ==========================================================
# Quasar — orquestador del ecosistema (Big Data + IA).
#
# Apps del ecosistema:
#   sociallab    Red social poliglota (Twitter + MongoDB + Neo4j + Spark ML)
#   preprolab    Preprocesamiento clasico del Tema 5 (Spark ETL + pandas/sklearn)
#   llmprep      Limpieza de corpus para LLMs (Spark ETL + BPE/MinHash)
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
                log "Arrancando SocialLab con la configuracion actual de $ENV_FILE"
            fi
            # Solo levanta SocialLab + sus dependencias (mongo, neo4j).
            # Si PreproLab esta corriendo, no la toca.
            compose up -d --build app-sociallab
            ok "Web:  http://localhost:8000"
            ok "Neo4j browser: http://localhost:7474  (neo4j / neo4jneo4j)"
            ;;

        down|stop)
            ensure_docker
            log "Parando SocialLab (mongo/neo4j siguen vivos para otras apps)..."
            compose stop app-sociallab
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
# PreproLab
# ==========================================================

PREPROLAB_SERVICE="app-preprolab"
PREPROLAB_BLOCKS="eda intermediate intermediate intermediate"  # placeholder

PREPROLAB_VALID_BLOCKS=(eda missing outliers integration transform normalize reduce_dim reduce_inst)

preprolab_restart_app() {
    log "Recreando el contenedor '$PREPROLAB_SERVICE' para recoger nuevos flags..."
    compose up -d "$PREPROLAB_SERVICE"
    ok "Listo. Recarga http://localhost:8002"
}

preprolab_usage() {
    cat <<EOF
PreproLab — comandos disponibles

Ciclo de vida:
    up                          Arranca app-preprolab + dependencias (mongo, neo4j).
    down                         Para SOLO app-preprolab (mongo/neo4j siguen vivos).
    status                       Muestra los flags actuales y el estado.
    restart                      Reinicia el contenedor app-preprolab.
    logs                         Sigue logs de app-preprolab.

Modo laboratorio (flags en infra/compose/.env.docker):
    unlock <bloque>             Desbloquea un bloque (lo marca como resuelto).
    lock   <bloque>             Vuelve a esconderlo (scaffold).
    solutions                    Desbloquea todos los bloques.
    exercises                    Bloquea todos los bloques (scaffold).
  Bloques validos: eda | missing | outliers | integration | transform | normalize | reduce_dim | reduce_inst

Pipeline de datos:
    seed                         Genera el dataset sintetico de robots (Fase 2 OK).
    etl                          Spark ETL: raw -> silver (parquet + perfil de calidad).

Web PreproLab: http://localhost:8002

Nota: En Fase 1 los bloques solo muestran placeholder. Se iran activando
segun avance el roadmap del ecosistema Quasar.
EOF
}

# Edicion del flag LAB_PREPROLAB (sin var de tipo neo4j/ml).
update_flag_preprolab() {
    local action="$1" block="$2"
    python3 - "$action" "$block" "$ENV_FILE" <<'PYEOF'
import re, sys

action, block, env_file = sys.argv[1:4]
ALL = {"eda", "missing", "outliers", "integration", "transform",
       "normalize", "reduce_dim", "reduce_inst"}

with open(env_file) as f:
    content = f.read()

m = re.search(r'^LAB_PREPROLAB=(.*)$', content, re.MULTILINE)
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
content = re.sub(r'^LAB_PREPROLAB=.*$', f'LAB_PREPROLAB={new_value}', content, flags=re.MULTILINE)

with open(env_file, "w") as f:
    f.write(content)

print(new_value if new_value else "(empty)")
PYEOF
}

preprolab_cmd() {
    local cmd="${1:-help}"
    shift || true

    case "$cmd" in
        up)
            ensure_docker
            log "Arrancando PreproLab con la configuracion actual de $ENV_FILE"
            compose up -d --build "$PREPROLAB_SERVICE"
            ok "Web: http://localhost:8002"
            ;;

        down|stop)
            ensure_docker
            log "Parando PreproLab (mongo/neo4j siguen vivos para otras apps)..."
            compose stop "$PREPROLAB_SERVICE"
            ;;

        restart)
            ensure_docker
            preprolab_restart_app
            ;;

        status)
            echo
            log "Estado del flag LAB_PREPROLAB ($ENV_FILE):"
            grep -E '^LAB_PREPROLAB=' "$ENV_FILE" | sed 's/^/    /'
            echo
            log "Servicios Docker (Quasar):"
            ensure_docker
            compose ps 2>/dev/null | sed 's/^/    /' || warn "Compose no esta corriendo"
            echo
            ;;

        unlock)
            local block="${1:-}"
            if [[ -z "$block" ]]; then
                err "Uso: ./lab.sh preprolab unlock <bloque>"
                echo "  Bloques: ${PREPROLAB_VALID_BLOCKS[*]}"
                exit 1
            fi
            new=$(update_flag_preprolab unlock "$block")
            ok "LAB_PREPROLAB = $new"
            ensure_docker
            preprolab_restart_app
            ;;

        lock)
            local block="${1:-}"
            if [[ -z "$block" ]]; then
                err "Uso: ./lab.sh preprolab lock <bloque>"
                exit 1
            fi
            new=$(update_flag_preprolab lock "$block")
            ok "LAB_PREPROLAB = $new"
            ensure_docker
            preprolab_restart_app
            ;;

        solutions)
            update_flag_preprolab all "" > /dev/null
            ok "Todo desbloqueado: LAB_PREPROLAB=all"
            ensure_docker
            preprolab_restart_app
            ;;

        exercises)
            update_flag_preprolab none "" > /dev/null
            ok "Todo en modo ejercicio (scaffold)"
            ensure_docker
            preprolab_restart_app
            ;;

        logs)
            ensure_docker
            compose logs -f "$PREPROLAB_SERVICE"
            ;;

        seed)
            ensure_docker
            log "Generando dataset sintetico de la flota de robots..."
            log "  Output: infra/data/preprolab/raw/{robots,sensors_readings,events,maintenances}.json"
            compose exec "$PREPROLAB_SERVICE" python -m src.seed.generate_robot_fleet
            ok "Seed completado. Datos en infra/data/preprolab/raw/"
            ;;

        cloud)
            local cloud_env="$DIR/apps/preprolab/.env.cloud"
            if [[ ! -f "$cloud_env" ]]; then
                err "Falta apps/preprolab/.env.cloud. Copia la plantilla y rellena las URIs:"
                echo "  cp apps/preprolab/.env.cloud.example apps/preprolab/.env.cloud"
                exit 1
            fi
            ensure_docker
            log "Arrancando PreproLab contra MongoDB cloud..."
            compose up -d --build "$PREPROLAB_SERVICE"
            ok "Web: http://localhost:8002"
            ;;

        etl)
            ensure_docker
            log "Spark ETL: raw -> silver (parquet columnar + perfil de calidad)..."
            log "  La suciedad del Tema 5 se PRESERVA (es el material del ejercicio)."
            compose exec "$PREPROLAB_SERVICE" python -m src.spark.run_pipeline
            ok "Silver listo. Los endpoints ya leen parquet. Output: infra/data/preprolab/silver/"
            ;;

        train)
            warn "Comando 'train' aun no implementado (roadmap del Tema 5)."
            exit 1
            ;;

        help|--help|-h|"")
            preprolab_usage
            ;;

        *)
            err "Comando desconocido: $cmd"
            preprolab_usage
            exit 1
            ;;
    esac
}

# ==========================================================
# LLM Lab
# ==========================================================

LLMPREP_SERVICE="app-llmprep"
LLMPREP_VALID_BLOCKS=(clean dedup tokenize train)

llmprep_restart_app() {
    log "Recreando el contenedor '$LLMPREP_SERVICE' para recoger nuevos flags..."
    compose up -d "$LLMPREP_SERVICE"
    ok "Listo. Recarga http://localhost:8001"
}

update_flag_llmprep() {
    local action="$1" block="$2"
    python3 - "$action" "$block" "$ENV_FILE" <<'PYEOF'
import re, sys
action, block, env_file = sys.argv[1:4]
ALL = {"clean", "dedup", "tokenize", "train"}
with open(env_file) as f:
    content = f.read()
m = re.search(r'^LAB_LLMPREP=(.*)$', content, re.MULTILINE)
current = m.group(1).strip() if m else ""
blocks = set(ALL) if current == "all" else {b.strip() for b in current.split(",") if b.strip()}
if action == "unlock":
    if block not in ALL:
        sys.stderr.write(f"Bloque desconocido: {block}. Validos: {sorted(ALL)}\n"); sys.exit(2)
    blocks.add(block)
elif action == "lock":
    blocks.discard(block)
elif action == "all":
    blocks = set(ALL)
elif action == "none":
    blocks = set()
else:
    sys.stderr.write(f"Action desconocida: {action}\n"); sys.exit(2)
new_value = ",".join(sorted(blocks))
content = re.sub(r'^LAB_LLMPREP=.*$', f'LAB_LLMPREP={new_value}', content, flags=re.MULTILINE)
with open(env_file, "w") as f:
    f.write(content)
print(new_value if new_value else "(empty)")
PYEOF
}

llmprep_usage() {
    cat <<EOF
LLM Lab — comandos disponibles

Ciclo de vida:
    up                          Arranca app-llmprep + dependencias.
    down                         Para SOLO app-llmprep.
    status                       Estado de los flags y servicios.
    restart                      Reinicia el contenedor.
    logs                         Sigue logs de app-llmprep.

Modo laboratorio (flags en infra/compose/.env.docker):
    unlock <bloque>             Desbloquea un bloque.
    lock   <bloque>             Vuelve a esconderlo (scaffold).
    solutions / exercises        Toggle masivo.
  Bloques: clean | dedup | tokenize | train

Pipeline (Fase 13+, en construccion):
    ingest                       Descargara Wikipedia ES + inyectara ruido.
    clean / tokenize / train     Bloques del pipeline.

Web LLM Lab: http://localhost:8001
EOF
}

llmprep_cmd() {
    local cmd="${1:-help}"
    shift || true
    case "$cmd" in
        up)
            ensure_docker
            log "Arrancando LLM Lab..."
            compose up -d --build "$LLMPREP_SERVICE"
            ok "Web: http://localhost:8001"
            ;;
        down|stop)
            ensure_docker
            log "Parando LLM Lab (mongo/neo4j siguen vivos)..."
            compose stop "$LLMPREP_SERVICE"
            ;;
        restart)
            ensure_docker
            llmprep_restart_app
            ;;
        status)
            echo
            log "Estado del flag LAB_LLMPREP ($ENV_FILE):"
            grep -E '^LAB_LLMPREP=' "$ENV_FILE" | sed 's/^/    /'
            echo
            ensure_docker
            compose ps 2>/dev/null | sed 's/^/    /' || warn "Compose no esta corriendo"
            echo
            ;;
        unlock)
            local block="${1:-}"
            if [[ -z "$block" ]]; then
                err "Uso: ./lab.sh llmprep unlock <bloque>"
                echo "  Bloques: ${LLMPREP_VALID_BLOCKS[*]}"; exit 1
            fi
            new=$(update_flag_llmprep unlock "$block"); ok "LAB_LLMPREP = $new"
            ensure_docker; llmprep_restart_app
            ;;
        lock)
            local block="${1:-}"
            if [[ -z "$block" ]]; then err "Uso: ./lab.sh llmprep lock <bloque>"; exit 1; fi
            new=$(update_flag_llmprep lock "$block"); ok "LAB_LLMPREP = $new"
            ensure_docker; llmprep_restart_app
            ;;
        solutions)
            update_flag_llmprep all "" > /dev/null; ok "Todo desbloqueado: LAB_LLMPREP=all"
            ensure_docker; llmprep_restart_app
            ;;
        exercises)
            update_flag_llmprep none "" > /dev/null; ok "Todo en modo ejercicio (scaffold)"
            ensure_docker; llmprep_restart_app
            ;;
        logs)
            ensure_docker; compose logs -f "$LLMPREP_SERVICE"
            ;;
        ingest)
            ensure_docker
            log "Generando corpus sucio (estilo Wikipedia ES dump)..."
            log "  Output: infra/data/llmprep/raw/corpus.json"
            compose exec "$LLMPREP_SERVICE" python -m src.ingest.generate_corpus
            ok "Corpus generado. Datos en infra/data/llmprep/raw/"
            ;;

        etl)
            ensure_docker
            log "Spark ETL: raw -> silver (parquet columnar + perfil de ruido)..."
            log "  La suciedad se PRESERVA (es el material de clean/dedup/tokenize)."
            compose exec "$LLMPREP_SERVICE" python -m src.spark.run_pipeline
            ok "Silver listo. Los endpoints ya leen parquet. Output: infra/data/llmprep/silver/"
            ;;

        clean|tokenize|train)
            warn "Comando '$cmd' aun no implementado (Fase 14-17 del roadmap)."
            exit 1
            ;;
        help|--help|-h|"")
            llmprep_usage
            ;;
        *)
            err "Comando desconocido: $cmd"; llmprep_usage; exit 1
            ;;
    esac
}

# ==========================================================
# StreamLab
# ==========================================================

STREAMLAB_SERVICE="app-streamlab"
STREAMLAB_VALID_BLOCKS=(windows late state)

streamlab_restart_app() {
    log "Recreando el contenedor '$STREAMLAB_SERVICE' para recoger nuevos flags..."
    compose up -d "$STREAMLAB_SERVICE"
    ok "Listo. Recarga http://localhost:8003"
}

update_flag_streamlab() {
    local action="$1" block="$2"
    python3 - "$action" "$block" "$ENV_FILE" <<'PYEOF'
import re, sys
action, block, env_file = sys.argv[1:4]
ALL = {"windows", "late", "state"}
with open(env_file) as f:
    content = f.read()
m = re.search(r'^LAB_STREAMLAB=(.*)$', content, re.MULTILINE)
current = m.group(1).strip() if m else ""
blocks = set(ALL) if current == "all" else {b.strip() for b in current.split(",") if b.strip()}
if action == "unlock":
    if block not in ALL:
        sys.stderr.write(f"Bloque desconocido: {block}. Validos: {sorted(ALL)}\n"); sys.exit(2)
    blocks.add(block)
elif action == "lock":
    blocks.discard(block)
elif action == "all":
    blocks = set(ALL)
elif action == "none":
    blocks = set()
else:
    sys.stderr.write(f"Action desconocida: {action}\n"); sys.exit(2)
new_value = ",".join(sorted(blocks))
content = re.sub(r'^LAB_STREAMLAB=.*$', f'LAB_STREAMLAB={new_value}', content, flags=re.MULTILINE)
with open(env_file, "w") as f:
    f.write(content)
print(new_value if new_value else "(empty)")
PYEOF
}

streamlab_usage() {
    cat <<EOF
StreamLab — comandos disponibles (Fase 1: esqueleto)

Ciclo de vida:
    up                           Arranca app-streamlab + dependencias.
    down                         Para SOLO app-streamlab.
    status                       Estado de los flags y servicios.
    restart                      Reinicia el contenedor.
    logs                         Sigue logs de app-streamlab.

Modo laboratorio (flags en infra/compose/.env.docker):
    unlock <bloque>              Desbloquea un bloque.
    lock   <bloque>              Vuelve a esconderlo (scaffold).
    solutions / exercises        Toggle masivo.
  Bloques: windows | late | state

Pipeline:
    emit [--lotes N] [--intervalo S]
                                 Emite telemetria de la flota en micro-lotes.
                                 --intervalo pone ritmo real (para verlo en vivo).

Web StreamLab: http://localhost:8003
EOF
}

streamlab_cmd() {
    local cmd="${1:-help}"
    shift || true
    case "$cmd" in
        up)
            ensure_docker
            log "Arrancando StreamLab..."
            compose up -d --build "$STREAMLAB_SERVICE"
            ok "Web: http://localhost:8003"
            ;;
        down|stop)
            ensure_docker
            log "Parando StreamLab (mongo sigue vivo)..."
            compose stop "$STREAMLAB_SERVICE"
            ;;
        restart)
            ensure_docker
            streamlab_restart_app
            ;;
        status)
            echo
            log "Estado del flag LAB_STREAMLAB ($ENV_FILE):"
            grep -E '^LAB_STREAMLAB=' "$ENV_FILE" | sed 's/^/    /'
            echo
            ensure_docker
            compose ps 2>/dev/null | sed 's/^/    /' || warn "Compose no esta corriendo"
            echo
            ;;
        unlock)
            local block="${1:-}"
            if [[ -z "$block" ]]; then
                err "Uso: ./lab.sh streamlab unlock <bloque>"
                echo "  Bloques: ${STREAMLAB_VALID_BLOCKS[*]}"; exit 1
            fi
            new=$(update_flag_streamlab unlock "$block"); ok "LAB_STREAMLAB = $new"
            ensure_docker; streamlab_restart_app
            ;;
        lock)
            local block="${1:-}"
            if [[ -z "$block" ]]; then err "Uso: ./lab.sh streamlab lock <bloque>"; exit 1; fi
            new=$(update_flag_streamlab lock "$block"); ok "LAB_STREAMLAB = $new"
            ensure_docker; streamlab_restart_app
            ;;
        solutions)
            update_flag_streamlab all "" > /dev/null; ok "Todo desbloqueado: LAB_STREAMLAB=all"
            ensure_docker; streamlab_restart_app
            ;;
        exercises)
            update_flag_streamlab none "" > /dev/null; ok "Todo en modo ejercicio (scaffold)"
            ensure_docker; streamlab_restart_app
            ;;
        logs)
            ensure_docker; compose logs -f "$STREAMLAB_SERVICE"
            ;;
        emit)
            ensure_docker
            log "Emitiendo telemetria de la flota (micro-lotes en raw/)..."
            log "  Output: infra/data/streamlab/raw/lote-*.json"
            compose exec "$STREAMLAB_SERVICE" python -m src.seed.emit_telemetry "$@"
            ok "Emision lista. Manifiesto en raw/_emision.json"
            ;;
        help|--help|-h|"")
            streamlab_usage
            ;;
        *)
            err "Comando desconocido: $cmd"; streamlab_usage; exit 1
            ;;
    esac
}

# ==========================================================
# Quasar Hub (app central :8080)
# ==========================================================

hub_cmd() {
    local cmd="${1:-help}"
    shift || true
    case "$cmd" in
        up)
            ensure_docker
            log "Arrancando el Quasar Hub..."
            compose up -d --build app-hub
            ok "Hub: http://localhost:8080  (puerta de entrada del ecosistema)"
            ;;
        down|stop)
            ensure_docker
            compose stop app-hub
            ;;
        restart)
            ensure_docker
            compose up -d app-hub
            ;;
        logs)
            ensure_docker
            compose logs -f app-hub
            ;;
        help|--help|-h|"")
            cat <<EOF
Quasar Hub — app central del ecosistema (:8080)

    up          Arranca el Hub.
    down        Para el Hub.
    restart     Reinicia el Hub.
    logs        Sigue logs del Hub.

El Hub es la puerta de entrada: landing explicativa, estado agregado de
las 3 apps, panel de configuración (desbloquear/bloquear bloques desde la
web) y guía de primeros pasos.

Web: http://localhost:8080
EOF
            ;;
        *)
            err "Comando desconocido: $cmd"; exit 1
            ;;
    esac
}

# ==========================================================
# Comandos globales (afectan a varias apps)
# ==========================================================

quasar_tour() {
    # Arranca el ecosistema completo + genera datos: demo en 1 comando.
    ensure_docker
    log "============================================================"
    log "  QUASAR TOUR — arrancando el ecosistema completo"
    log "============================================================"
    echo

    log "[1/4] Arrancando mongo + neo4j + las apps + el Hub..."
    compose up -d --build mongodb neo4j app-hub app-sociallab app-preprolab app-llmprep
    echo

    log "[2/4] Esperando a que mongo y neo4j esten healthy..."
    local tries=0
    while (( tries < 24 )); do
        local m n
        m=$(docker inspect quasar-mongo --format='{{.State.Health.Status}}' 2>/dev/null || echo none)
        n=$(docker inspect quasar-neo4j --format='{{.State.Health.Status}}' 2>/dev/null || echo none)
        if [[ "$m" == "healthy" && "$n" == "healthy" ]]; then
            ok "mongo + neo4j healthy"
            break
        fi
        sleep 5
        ((tries++))
    done
    echo

    log "[3/4] Seed + ETL de SocialLab (red social poliglota)..."
    compose exec -T app-sociallab python -m src.seed.generate_dirty_data || warn "seed sociallab fallo"
    compose exec -T app-sociallab python -m src.spark.run_pipeline --all || warn "etl sociallab fallo"
    echo

    log "[4/4] Seed + ETL de PreproLab (flota de robots) y LLM Lab (corpus)..."
    compose exec -T app-preprolab python -m src.seed.generate_robot_fleet || warn "seed preprolab fallo"
    compose exec -T app-preprolab python -m src.spark.run_pipeline || warn "etl preprolab fallo"
    compose exec -T app-llmprep python -m src.ingest.generate_corpus || warn "ingest llmprep fallo"
    compose exec -T app-llmprep python -m src.spark.run_pipeline || warn "etl llmprep fallo"
    echo

    ok "============================================================"
    ok "  Ecosistema Quasar arriba:"
    ok "    ★ Hub:         http://localhost:8080  (EMPIEZA AQUÍ)"
    ok "    SocialLab:     http://localhost:8000"
    ok "    LLM Lab:       http://localhost:8001"
    ok "    PreproLab:     http://localhost:8002  (Pipeline Studio ★)"
    ok "    Neo4j browser: http://localhost:7474  (neo4j / neo4jneo4j)"
    ok "============================================================"
}

quasar_all_solutions() {
    ensure_docker
    log "Desbloqueando TODOS los bloques de TODAS las apps..."
    update_flag LAB_NEO4J all "" > /dev/null
    update_flag LAB_ML all "" > /dev/null
    update_flag_preprolab all "" > /dev/null
    update_flag_llmprep all "" > /dev/null
    ok "LAB_NEO4J=all, LAB_ML=all, LAB_PREPROLAB=all, LAB_LLMPREP=all"
    compose up -d app-sociallab app-preprolab app-llmprep
    ok "Apps reiniciadas con todas las soluciones activas."
}

quasar_all_exercises() {
    ensure_docker
    log "Bloqueando TODOS los bloques de TODAS las apps (modo alumno)..."
    update_flag LAB_NEO4J none "" > /dev/null
    update_flag LAB_ML none "" > /dev/null
    update_flag_preprolab none "" > /dev/null
    update_flag_llmprep none "" > /dev/null
    ok "Todos los flags vacios — todo en modo ejercicio (scaffold)."
    compose up -d app-sociallab app-preprolab app-llmprep
    ok "Apps reiniciadas en modo ejercicio."
}

quasar_down_all() {
    ensure_docker
    log "Parando TODO el ecosistema (volumenes preservados)..."
    compose down
}

# ==========================================================
# Distribucion para alumnos
# ==========================================================

# Regenera la copia sin soluciones y la sincroniza contra el repo publico
# de alumnos, dejandola commiteada. El push se confirma a mano: es lo que
# hace publico el contenido.
quasar_dist() {
    local target="${1:-$DIR/../quasar-alumnos}"
    local tmp
    tmp="$(mktemp -d)"
    trap 'rm -rf "$tmp"' RETURN

    log "Generando copia sin soluciones..."
    if ! "$DIR/tools/make_student_dist.sh" "$tmp/dist" > "$tmp/log" 2>&1; then
        cat "$tmp/log"
        err "No se pudo generar la copia"
        return 1
    fi
    grep -E 'retirados|Revisado' "$tmp/log" | sed 's/^/  /' || true

    if [ ! -d "$target/.git" ]; then
        mkdir -p "$(dirname "$target")"
        mv "$tmp/dist" "$target"
        ok "Copia creada en $target"
        echo
        echo "Es la primera vez, asi que falta enlazarla con el repo de alumnos:"
        echo "  cd $target"
        echo "  git init -b main && git add -A && git commit -m 'Quasar'"
        echo "  gh repo create <usuario>/Quasar --public --source=. --push"
        return 0
    fi

    log "Sincronizando con $target"
    rsync -a --delete --exclude '.git' "$tmp/dist/" "$target/"

    cd "$target"
    git add -A
    if git diff --cached --quiet; then
        ok "El repo de alumnos ya estaba al dia (sin cambios)"
        return 0
    fi

    echo
    log "Cambios que se publicarian:"
    git -c color.status=always status --short | sed 's/^/  /'
    echo

    git commit -q -m "Actualiza la plataforma desde el repo de desarrollo"
    ok "Commit hecho en $target"
    echo
    warn "Falta subirlo (esto lo hace publico):"
    echo "  cd $target && git push"
}

# ==========================================================
# Top-level routing
# ==========================================================

quasar_usage() {
    cat <<EOF
Quasar — laboratorio Big Data + IA (multi-app).

Uso:    ./lab.sh <app> <comando> [args]
        ./lab.sh <comando-global>

Apps disponibles:
    sociallab    Red social poliglota (Twitter + MongoDB + Neo4j + Spark ML)
                 18 ejercicios en 3 bloques Cypher + 3 bloques ML.
    preprolab    Preprocesamiento clasico (Tema 5) — COMPLETO
                 8 bloques + Pipeline Studio. 37 ejercicios.

    llmprep      Limpieza de corpus para LLMs (LLM Lab) — completa.
                 Bloques: clean, dedup, tokenize, train. 18 ejercicios.
    streamlab    Datos en tiempo real (StreamLab) — en construccion.
                 Bloques: windows, late, state. 18 ejercicios.

Comandos globales (afectan a TODAS las apps):
    tour                         Arranca el ecosistema completo + seed + ETL.
                                 Demo en 1 comando (~2-3 min).
    all-solutions                Desbloquea todos los bloques de todas las apps.
    all-exercises                Bloquea todo (modo alumno) en todas las apps.
    down-all                     Para todo el ecosistema.
    dist [ruta]                  Actualiza la copia para alumnos (sin soluciones)
                                 y la deja lista para subir al repo publico.

Comandos por app (varian):
    up [exercises|solutions]    Arranca la app
    down                        Para los contenedores
    seed                        Genera datos
    etl                         Ejecuta el pipeline ETL
    train                       Entrena modelos ML
    status                      Estado actual
    unlock / lock <kind> <bloque>  Gestiona ejercicios
    cloud                       Arranca contra Atlas/Aura
    reset                       Borra todos los datos

Ayuda especifica:
    ./lab.sh sociallab help
    ./lab.sh preprolab help

Ejemplos:
    ./lab.sh tour                         # todo el ecosistema en 1 comando
    ./lab.sh sociallab up exercises
    ./lab.sh preprolab seed
    ./lab.sh all-solutions                # destapa todo para una demo
EOF
}

app="${1:-help}"
shift || true

case "$app" in
    sociallab)
        sociallab_cmd "$@"
        ;;
    preprolab)
        preprolab_cmd "$@"
        ;;
    llmprep)
        llmprep_cmd "$@"
        ;;
    streamlab)
        streamlab_cmd "$@"
        ;;
    hub)
        hub_cmd "$@"
        ;;
    tour)
        quasar_tour
        ;;
    all-solutions)
        quasar_all_solutions
        ;;
    all-exercises)
        quasar_all_exercises
        ;;
    down-all)
        quasar_down_all
        ;;
    dist)
        quasar_dist "$@"
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
