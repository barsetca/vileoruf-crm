from typing import Annotated

from fastapi import Depends, HTTPException, status

from backend.app.api.dependencies import get_current_user
from backend.app.models import User
from backend.app.services.ai.rate_limit import AIRateLimitExceeded, enforce_manual_ai_rate_limit


def require_manual_ai_launch_quota(current_user: Annotated[User, Depends(get_current_user)]) -> None:
    try:
        enforce_manual_ai_rate_limit(current_user.id)
    except AIRateLimitExceeded as error:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many AI launch requests. Please retry later.", headers={"Retry-After": str(error.retry_after_seconds)}) from error
