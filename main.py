"""Entry point — python main.py"""

import uvicorn
from src.config import WEB_HOST, WEB_PORT, WEB_DEBUG

if __name__ == "__main__":
    uvicorn.run(
        "src.web.app:app",
        host=WEB_HOST,
        port=WEB_PORT,
        reload=WEB_DEBUG,
    )
