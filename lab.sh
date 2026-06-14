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
PreproLab — comandos disponibles (Fase 1: esqueleto)

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
    etl                          Ejecutara los bloques del pipeline (Fase 3+).

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

        etl|train)
            warn "Comando '$cmd' aun no implementado en Fase $([ "$cmd" = "etl" ] && echo "3+" || echo "futura")."
            echo "  Se a\xc3\xb1adira segun avance el roadmap del Tema 5."
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
# Comandos globales (afectan a varias apps)
# ==========================================================

quasar_tour() {
    # Arranca el ecosistema completo + genera datos: demo en 1 comando.
    ensure_docker
    log "============================================================"
    log "  QUASAR TOUR — arrancando el ecosistema completo"
    log "============================================================"
    echo

    log "[1/4] Arrancando mongo + neo4j + las apps..."
    compose up -d --build mongodb neo4j app-sociallab app-preprolab
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

    log "[4/4] Seed de PreproLab (flota de robots)..."
    compose exec -T app-preprolab python -m src.seed.generate_robot_fleet || warn "seed preprolab fallo"
    echo

    ok "============================================================"
    ok "  Ecosistema Quasar arriba:"
    ok "    SocialLab:     http://localhost:8000"
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
    ok "LAB_NEO4J=all, LAB_ML=all, LAB_PREPROLAB=all"
    compose up -d app-sociallab app-preprolab
    ok "Apps reiniciadas con todas las soluciones activas."
}

quasar_all_exercises() {
    ensure_docker
    log "Bloqueando TODOS los bloques de TODAS las apps (modo alumno)..."
    update_flag LAB_NEO4J none "" > /dev/null
    update_flag LAB_ML none "" > /dev/null
    update_flag_preprolab none "" > /dev/null
    ok "Todos los flags vacios — todo en modo ejercicio (scaffold)."
    compose up -d app-sociallab app-preprolab
    ok "Apps reiniciadas en modo ejercicio."
}

quasar_down_all() {
    ensure_docker
    log "Parando TODO el ecosistema (volumenes preservados)..."
    compose down
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
                 33 ejercicios en 3 bloques Cypher + 3 bloques ML.
    preprolab    Preprocesamiento clasico (Tema 5) — COMPLETO
                 8 bloques + Pipeline Studio. ~46 ejercicios.

Apps planificadas (proximamente):
    llmprep      Limpieza de corpus + nanoGPT (Fase posterior del roadmap).

Comandos globales (afectan a TODAS las apps):
    tour                         Arranca el ecosistema completo + seed + ETL.
                                 Demo en 1 comando (~2-3 min).
    all-solutions                Desbloquea todos los bloques de todas las apps.
    all-exercises                Bloquea todo (modo alumno) en todas las apps.
    down-all                     Para todo el ecosistema.

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
        warn "La app 'llmprep' aun no esta implementada."
        echo "  Esta planificada para una fase posterior del roadmap de Quasar."
        exit 1
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
    help|--help|-h|"")
        quasar_usage
        ;;
    *)
        err "App desconocida: $app"
        quasar_usage
        exit 1
        ;;
esac
