#!/usr/bin/env bash
# ==========================================================
# Genera la copia de Quasar que reciben los alumnos: igual que
# este repo pero SIN los ficheros de solución.
#
#   ./tools/make_student_dist.sh [destino]
#
# Qué quita:
#   - Cada `<bloque>.py` que tenga su pareja `<bloque>_ex.py`.
#   - Los modelos ML resueltos de SocialLab (src/spark/models/*),
#     salvo el orquestador run_all.py.
#   - Los tests que comprueban las soluciones (delatan el resultado).
#
# Qué NO quita: scaffolds, seeds, ETL, web, infra, docs. La plataforma
# funciona igual; lo único que no está es la respuesta.
#
# Por qué esto y no una contraseña: mientras los ficheros solución
# existan, se leen desde el editor sin pasar por la web. Un flag solo
# puede destapar lo que está; si no está, no hay nada que destapar.
#
# El árbol resultante NO lleva historial de git: es el punto de partida
# del repo público de alumnos. Sube ahí las soluciones de cada bloque
# cuando su entrega haya cerrado.
# ==========================================================

set -euo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${1:-$DIR/../quasar-alumnos}"

GREEN='\033[0;32m'; BLUE='\033[0;34m'; YELLOW='\033[0;33m'; NC='\033[0m'
log()  { echo -e "${BLUE}[dist]${NC} $1"; }
ok()   { echo -e "${GREEN}[OK]${NC}  $1"; }
warn() { echo -e "${YELLOW}[!]${NC}  $1"; }

if [ -e "$DEST" ]; then
    echo "El destino ya existe: $DEST"
    echo "Borra esa carpeta o indica otra ruta:  ./tools/make_student_dist.sh <destino>"
    exit 1
fi

log "Copiando el repo (sin .git ni datos generados) a $DEST"
mkdir -p "$DEST"
# Copiamos solo lo que git rastrea: nada de .env, datos del lake ni caches.
( cd "$DIR" && git ls-files -z ) | while IFS= read -r -d '' f; do
    mkdir -p "$DEST/$(dirname "$f")"
    cp "$DIR/$f" "$DEST/$f"
done

log "Quitando las soluciones"
removed=0

# 1. Bloques con pareja scaffold: si existe <x>_ex.py, fuera <x>.py
while IFS= read -r ex; do
    sol="${ex%_ex.py}.py"
    if [ -f "$DEST/$sol" ]; then
        rm "$DEST/$sol"
        echo "    - $sol"
        removed=$((removed + 1))
    fi
done < <(cd "$DEST" && find . -name '*_ex.py' | sed 's|^\./||')

# 2. Modelos ML resueltos de SocialLab (run_all.py es el orquestador, se queda)
models="$DEST/apps/sociallab/src/spark/models"
if [ -d "$models" ]; then
    while IFS= read -r m; do
        base="$(basename "$m")"
        [ "$base" = "run_all.py" ] && continue
        [ "$base" = "__init__.py" ] && continue
        rm "$m"
        echo "    - ${m#$DEST/}"
        removed=$((removed + 1))
    done < <(find "$models" -name '*.py')
fi

# 3. Tests que verifican soluciones (revelan resultados esperados)
for t in test_preprolab_algorithms.py test_llmprep_clean.py test_llmprep_dedup.py; do
    if [ -f "$DEST/tests/$t" ]; then
        rm "$DEST/tests/$t"
        echo "    - tests/$t"
        removed=$((removed + 1))
    fi
done

ok "$removed ficheros de solución retirados"

# Comprobación: que no quede ninguna solución con pareja scaffold.
leftover=0
while IFS= read -r ex; do
    sol="${ex%_ex.py}.py"
    [ -f "$DEST/$sol" ] && { warn "sigue presente: $sol"; leftover=$((leftover + 1)); }
done < <(cd "$DEST" && find . -name '*_ex.py' | sed 's|^\./||')

if [ "$leftover" -gt 0 ]; then
    echo "Revisión fallida: quedan $leftover soluciones. No subas esta copia."
    exit 1
fi
ok "Revisado: no queda ninguna solución con pareja scaffold"

cat > "$DEST/SOLUCIONES.md" <<'EOF'
# Sobre las soluciones

Esta copia trae los ejercicios (`*_ex.py`) pero no las soluciones.

Los interruptores del Hub (pestaña **Configuración**, o el botón dentro de
cada concepto en **Aprende**) siguen funcionando: sencillamente no tienen
nada que destapar todavía. Cuando cierre la entrega de un bloque, se
publican sus soluciones aquí; al actualizar el repo, esos interruptores ya
te mostrarán el código resuelto para estudiarlo.

Mientras tanto, la plataforma funciona entera: datos, ETL, web y tus
propias implementaciones.
EOF

echo
ok "Copia para alumnos lista en: $DEST"
echo
echo "Siguientes pasos:"
echo "  cd $DEST"
echo "  git init && git add -A && git commit -m 'Quasar — versión para alumnos'"
echo "  git remote add origin <URL del repo público>"
echo "  git push -u origin main"
echo
warn "Importante: el repo público debe empezar con historial NUEVO."
echo "  Si publicas el historial de este repo, las soluciones siguen"
echo "  siendo accesibles en los commits anteriores."
