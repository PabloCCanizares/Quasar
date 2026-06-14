"""Configuración de pytest para Quasar.

Carga los módulos puros de las apps por ruta de archivo (evitando colisiones
con módulos stdlib como `tokenize`) y los expone bajo nombres únicos:

    import quasar_bpe      → apps/llmprep/src/tokenize/bpe.py
    import quasar_ngram    → apps/llmprep/src/train/ngram_lm.py

También añade la raíz del repo al path para `infra.shared`.
"""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# Cargar módulos puros bajo nombres no colisionantes.
_load("quasar_bpe", ROOT / "apps" / "llmprep" / "src" / "tokenize" / "bpe.py")
_load("quasar_ngram", ROOT / "apps" / "llmprep" / "src" / "train" / "ngram_lm.py")
