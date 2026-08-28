from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import get_frontend_settings


app = FastAPI()
frontend_settings = get_frontend_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_settings.frontend_origin],
    allow_methods=["GET"],
    allow_headers=[],
)


@app.get("/health", status_code=status.HTTP_200_OK)
async def health() -> dict[str, str]:
    return {"status": "ok"}
