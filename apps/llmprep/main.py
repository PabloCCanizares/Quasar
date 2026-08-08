"""LLM Lab entry point — `python main.py` o `python -m apps.llmprep.main`.

Bootstrap del sys.path para que `infra.shared.*` sea importable tanto en
modo Docker como nativo.
"""

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
for candidate in (_HERE, _HERE.parent.parent):  # apps/llmprep y Quasar/
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import uvicorn  # noqa: E402
from src.config import WEB_DEBUG, WEB_HOST, WEB_PORT  # noqa: E402

if __name__ == "__main__":
    uvicorn.run(
        "src.web.app:app",
        host=WEB_HOST,
        port=WEB_PORT,
        reload=WEB_DEBUG,
    )
