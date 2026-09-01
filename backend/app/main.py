from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.auth.router import router as auth_router
from backend.app.api.clients.router import router as clients_router
from backend.app.api.deals.router import router as deals_router
from backend.app.api.employees.router import router as employees_router
from backend.app.api.pipeline_stages.router import router as pipeline_stages_router
from backend.app.api.public.router import router as public_router
from backend.app.api.users.router import router as users_router
from backend.app.core.config import get_frontend_settings


app = FastAPI()
frontend_settings = get_frontend_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(auth_router)
app.include_router(clients_router)
app.include_router(deals_router)
app.include_router(employees_router)
app.include_router(pipeline_stages_router)
app.include_router(public_router)
app.include_router(users_router)


@app.get("/health", status_code=status.HTTP_200_OK)
async def health() -> dict[str, str]:
    return {"status": "ok"}
