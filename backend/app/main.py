from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.auth.router import router as auth_router
from backend.app.api.ai.router import router as ai_router
from backend.app.api.ai.deal_prediction_router import router as deal_prediction_router
from backend.app.api.ai.next_best_action_router import router as next_best_action_router
from backend.app.api.ai.email_draft_router import draft_router as email_drafts_router, generation_router as email_draft_router
from backend.app.api.ai.settings_router import router as ai_settings_router
from backend.app.api.ai.history_router import router as ai_history_router
from backend.app.api.business.router import router as business_router
from backend.app.api.clients.router import router as clients_router
from backend.app.api.communications.router import router as communications_router
from backend.app.api.deals.router import router as deals_router
from backend.app.api.employees.router import router as employees_router
from backend.app.api.pipeline_stages.router import router as pipeline_stages_router
from backend.app.api.public.router import router as public_router
from backend.app.api.tasks.router import router as tasks_router
from backend.app.api.users.router import router as users_router
from backend.app.api.integrations.router import router as integrations_router
from backend.app.api.integrations.telegram_webhook import router as telegram_webhook_router
from backend.app.core.config import get_frontend_settings


app = FastAPI()
frontend_settings = get_frontend_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(auth_router)
app.include_router(ai_router)
app.include_router(deal_prediction_router)
app.include_router(next_best_action_router)
app.include_router(email_draft_router)
app.include_router(email_drafts_router)
app.include_router(ai_settings_router)
app.include_router(ai_history_router)
app.include_router(business_router)
app.include_router(clients_router)
app.include_router(communications_router)
app.include_router(deals_router)
app.include_router(employees_router)
app.include_router(pipeline_stages_router)
app.include_router(public_router)
app.include_router(tasks_router)
app.include_router(users_router)
app.include_router(integrations_router)
app.include_router(telegram_webhook_router)


@app.get("/health", status_code=status.HTTP_200_OK)
async def health() -> dict[str, str]:
    return {"status": "ok"}
