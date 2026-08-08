"""Configuración de pytest para Quasar.

Carga los módulos puros de las apps por ruta de archivo (evitando colisiones
con módulos stdlib como `tokenize`) y los expone bajo nombres únicos:

    import quasar_bpe          → apps/llmprep/src/tokenize/bpe.py
    import quasar_ngram        → apps/llmprep/src/train/ngram_lm.py
    import quasar_clean        → apps/llmprep/src/web/routes/clean.py
    import quasar_dedup        → apps/llmprep/src/web/routes/dedup.py
    import quasar_transform    → apps/preprolab/src/web/routes/transform.py
    import quasar_integration  → apps/preprolab/src/web/routes/integration.py

Los módulos de rutas importan `fastapi` y `src.web.data_loader` /
`src.web.corpus_loader` en el top. Para poder cargarlos y testear solo sus
funciones puras (sin levantar la pila web ni tocar disco), instalamos stubs
mínimos de esos módulos en `sys.modules` antes de cargarlos.
"""

import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load(module_name: str, file_path: Path):
    """Carga un módulo por ruta. Devuelve None si el fichero no está.

    En la copia que reciben los alumnos los módulos solución no se
    incluyen (ver tools/make_student_dist.sh). Los tests que dependen de
    ellos se saltan solos en vez de romper la recogida entera.
    """
    if not file_path.exists():
        return None
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# ------------------------------------------------------------------
# Stub de fastapi: permite importar los módulos de rutas sin instalar
# starlette/pydantic. Solo cubre lo que se usa en tiempo de import
# (APIRouter + sus decoradores, HTTPException, Query).
# ------------------------------------------------------------------
def _install_fake_fastapi() -> None:
    if "fastapi" in sys.modules:
        return
    fastapi = types.ModuleType("fastapi")

    class APIRouter:
        def __init__(self, *args, **kwargs):
            pass

        def _decorator(self, *args, **kwargs):
            def wrap(fn):
                return fn
            return wrap

        get = post = put = patch = delete = _decorator

    class HTTPException(Exception):
        def __init__(self, status_code: int = 400, detail=None):
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    def Query(default=None, *args, **kwargs):
        return default

    fastapi.APIRouter = APIRouter
    fastapi.HTTPException = HTTPException
    fastapi.Query = Query
    sys.modules["fastapi"] = fastapi


# ------------------------------------------------------------------
# Stubs de los cargadores de datos de cada app. Las funciones puras que
# testeamos reciben sus datos por argumento, así que estos stubs solo
# existen para que el `from src.web... import ...` del top resuelva.
# ------------------------------------------------------------------
def _install_fake_src() -> None:
    for pkg in ("src", "src.web"):
        if pkg not in sys.modules:
            mod = types.ModuleType(pkg)
            mod.__path__ = []  # marcarlo como paquete
            sys.modules[pkg] = mod

    data_loader = types.ModuleType("src.web.data_loader")
    data_loader.TABLES = ["robots", "sensors_readings", "events", "maintenances"]
    data_loader.load_table = lambda name: (_ for _ in ()).throw(
        RuntimeError("load_table está stubbeado en los tests")
    )
    sys.modules["src.web.data_loader"] = data_loader

    corpus_loader = types.ModuleType("src.web.corpus_loader")
    corpus_loader.load_corpus = lambda: []
    corpus_loader.is_ingested = lambda: False
    sys.modules["src.web.corpus_loader"] = corpus_loader

    config = types.ModuleType("src.config")
    sys.modules["src.config"] = config


_install_fake_fastapi()
_install_fake_src()

# Módulos puros sin dependencias web.
_load("quasar_bpe", ROOT / "apps" / "llmprep" / "src" / "tokenize" / "bpe.py")
_load("quasar_ngram", ROOT / "apps" / "llmprep" / "src" / "train" / "ngram_lm.py")

# Módulos de rutas: se cargan gracias a los stubs de arriba. Exponen las
# funciones puras (limpieza, MinHash/LSH, MDLP, Cramér's V) que testeamos.
_load("quasar_clean", ROOT / "apps" / "llmprep" / "src" / "web" / "routes" / "clean.py")
_load("quasar_dedup", ROOT / "apps" / "llmprep" / "src" / "web" / "routes" / "dedup.py")
_load("quasar_transform", ROOT / "apps" / "preprolab" / "src" / "web" / "routes" / "transform.py")
_load("quasar_integration", ROOT / "apps" / "preprolab" / "src" / "web" / "routes" / "integration.py")
