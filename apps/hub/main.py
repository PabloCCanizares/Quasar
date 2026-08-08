"""Quasar Hub entry point — la app central del ecosistema.

Bootstrap del sys.path para infra.shared, igual que las otras apps.
"""

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
for candidate in (_HERE, _HERE.parent.parent):  # apps/hub y Quasar/
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import uvicorn  # noqa: E402
from src.config import WEB_HOST, WEB_PORT, WEB_DEBUG  # noqa: E402

if __name__ == "__main__":
    uvicorn.run("src.web.app:app", host=WEB_HOST, port=WEB_PORT, reload=WEB_DEBUG)
