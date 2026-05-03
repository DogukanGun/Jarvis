"""Legal RAG agent — entry point."""

import uvicorn
from app.config import config

if __name__ == "__main__":
    uvicorn.run("app.server:app", host="0.0.0.0", port=config.PORT, reload=False)
