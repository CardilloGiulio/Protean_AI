from fastapi import APIRouter, HTTPException, Request, Response, status

from protean_workspace.models.api import AuthRequest, AuthStatusResponse, UserResponse
from protean_workspace.services.auth import AuthenticationError, SetupUnavailableError

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_session_cookie(request: Request, response: Response, token: str) -> None:
    settings = request.app.state.settings
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.access_token_minutes * 60,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="strict",
        path="/",
    )


@router.get("/status", response_model=AuthStatusResponse)
def auth_status(request: Request) -> AuthStatusResponse:
    auth = request.app.state.auth_service
    initialized = auth.is_initialized()
    token = request.cookies.get(request.app.state.settings.session_cookie_name)
    if not token:
        return AuthStatusResponse(initialized=initialized, authenticated=False)
    try:
        user, _ = auth.authenticate(token)
    except AuthenticationError:
        return AuthStatusResponse(initialized=initialized, authenticated=False)
    return AuthStatusResponse(initialized=initialized, authenticated=True, username=user.username)


@router.post("/setup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def setup(request: Request, payload: AuthRequest, response: Response) -> UserResponse:
    try:
        session = request.app.state.auth_service.setup_owner(payload.username, payload.password)
    except SetupUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    _set_session_cookie(request, response, session.token)
    return UserResponse(id=session.user.id, username=session.user.username)


@router.post("/login", response_model=UserResponse)
def login(request: Request, payload: AuthRequest, response: Response) -> UserResponse:
    try:
        session = request.app.state.auth_service.login(payload.username, payload.password)
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    _set_session_cookie(request, response, session.token)
    return UserResponse(id=session.user.id, username=session.user.username)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response) -> Response:
    settings = request.app.state.settings
    token = request.cookies.get(settings.session_cookie_name)
    user_id = request.app.state.auth_service.logout(token)
    if user_id is not None:
        request.app.state.assistant_service.close_user_sessions(user_id)
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
