"""SocialLab entry point — `python main.py` o `python -m apps.sociallab.main`.

Bootstrap del sys.path para que `infra.shared.*` sea importable tanto en modo
Docker (WORKDIR=/app, infra/shared montado en /app/infra/shared) como en modo
nativo (ejecución desde apps/sociallab/).
"""

import sys
from pathlib import Path

# Asegura que la raíz del repo (Quasar/) esté en sys.path para que
# `from infra.shared.X import ...` funcione en cualquier modo de arranque.
_HERE = Path(__file__).resolve().parent
for candidate in (_HERE, _HERE.parent.parent):  # apps/sociallab y Quasar/
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import uvicorn  # noqa: E402
from src.config import WEB_HOST, WEB_PORT, WEB_DEBUG  # noqa: E402

if __name__ == "__main__":
    uvicorn.run(
        "src.web.app:app",
        host=WEB_HOST,
        port=WEB_PORT,
        reload=WEB_DEBUG,
    )
