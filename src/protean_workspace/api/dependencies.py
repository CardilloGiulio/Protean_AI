from fastapi import HTTPException, Request, status

from protean_workspace.models.domain import User
from protean_workspace.services.auth import AuthenticationError


def get_current_user(request: Request) -> User:
    settings = request.app.state.settings
    token = request.cookies.get(settings.session_cookie_name)
    try:
        user, _ = request.app.state.auth_service.authenticate(token)
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return user
