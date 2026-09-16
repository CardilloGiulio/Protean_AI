from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import FileResponse

from protean_workspace.api.dependencies import get_current_user
from protean_workspace.desktop.launcher import AssistantDesktopLaunchError
from protean_workspace.models.api import (
    AssistantAvailabilityResponse,
    AssistantCloseResponse,
    AssistantEventRequest,
    AssistantEventResponse,
    AssistantSessionResponse,
    AssistantStartRequest,
    AssistantStartResponse,
    AssistantWardrobeChangeRequest,
    AssistantWardrobeChangeResponse,
)
from protean_workspace.models.domain import User
from protean_workspace.services.assistant import (
    AssistantServiceError,
    AssistantSessionNotFoundError,
    AssistantUnavailableError,
)

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


def _bearer(authorization: str | None) -> str:
    value = str(authorization or "").strip()
    if not value.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Virtual Assistant bearer token required")
    return value.split(" ", 1)[1].strip()


def _session(request: Request, authorization: str | None):
    try:
        return request.app.state.assistant_service.authenticate(_bearer(authorization))
    except AssistantSessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.get("/availability", response_model=AssistantAvailabilityResponse)
def availability(request: Request, user: User = Depends(get_current_user)) -> AssistantAvailabilityResponse:
    return AssistantAvailabilityResponse(**request.app.state.assistant_service.availability(user.id))


@router.post("/start", response_model=AssistantStartResponse, status_code=status.HTTP_201_CREATED)
async def start_assistant(
    request: Request,
    payload: AssistantStartRequest,
    user: User = Depends(get_current_user),
) -> AssistantStartResponse:
    session = None
    try:
        session = await request.app.state.assistant_service.start(
            user.id,
            character_id=payload.character_id,
            phase_id=payload.phase_id,
            scenario_id=payload.scenario_id,
            custom_scenario=payload.custom_scenario.model_dump() if payload.custom_scenario else None,
            tone_id=payload.tone_id,
            wardrobe_id=payload.wardrobe_id,
            background_mode=payload.background_mode,
            custom_background_data_url=payload.custom_background_data_url,
            custom_background_name=payload.custom_background_name,
        )
        request.app.state.assistant_desktop_launcher.launch(
            base_url=str(request.base_url).rstrip("/"),
            session_token=session.token,
        )
    except AssistantDesktopLaunchError as exc:
        if session is not None:
            request.app.state.assistant_service.close(session.token, user_id=user.id)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AssistantUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AssistantServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return AssistantStartResponse(
        launched=True,
        character_name=session.character_name,
        phase_name=session.phase_name,
        scenario_name=session.scenario.name,
        tone_name=session.tone_name,
        wardrobe_label=session.wardrobe_label,
    )


@router.get("/session", response_model=AssistantSessionResponse)
def session_state(request: Request, authorization: str | None = Header(default=None)) -> AssistantSessionResponse:
    session = _session(request, authorization)
    return AssistantSessionResponse(**request.app.state.assistant_service.session_payload(session))


@router.post("/session/events", response_model=AssistantEventResponse)
async def event(
    request: Request,
    payload: AssistantEventRequest,
    authorization: str | None = Header(default=None),
) -> AssistantEventResponse:
    session = _session(request, authorization)
    try:
        reply = await request.app.state.assistant_service.event(
            session,
            event_type=payload.event_type,
            input_type=payload.input_type,
            text=payload.text,
            query=payload.query,
            poke_count=payload.poke_count,
            old_wardrobe_id=payload.old_wardrobe_id,
            new_wardrobe_id=payload.new_wardrobe_id,
            screen=payload.screen.model_dump() if payload.screen else None,
        )
    except AssistantUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AssistantServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    payload_state = request.app.state.assistant_service.session_payload(session)
    return AssistantEventResponse(
        reaction=reply.reaction,
        remark=reply.remark,
        wardrobe_id=session.wardrobe_id,
        wardrobe_label=session.wardrobe_label,
        sprite_paths=payload_state["sprite_paths"],
    )


@router.post("/session/wardrobe", response_model=AssistantWardrobeChangeResponse)
def wardrobe(
    request: Request,
    payload: AssistantWardrobeChangeRequest,
    authorization: str | None = Header(default=None),
) -> AssistantWardrobeChangeResponse:
    session = _session(request, authorization)
    try:
        result = request.app.state.assistant_service.change_wardrobe_locally(session, payload.wardrobe_id)
    except AssistantUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return AssistantWardrobeChangeResponse(**result)


@router.get("/session/background")
def background(request: Request, authorization: str | None = Header(default=None)) -> FileResponse:
    session = _session(request, authorization)
    path = request.app.state.assistant_service.custom_background_path(session)
    if path is None or not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No custom background for this session")
    return FileResponse(path, media_type="image/webp", headers={"Cache-Control": "no-store"})


@router.post("/session/close", response_model=AssistantCloseResponse)
def close(request: Request, authorization: str | None = Header(default=None)) -> AssistantCloseResponse:
    token = _bearer(authorization)
    _session(request, authorization)
    request.app.state.assistant_service.close(token)
    return AssistantCloseResponse(closed=True)
