from fastapi import APIRouter, Depends, HTTPException, Request, status

from protean_workspace.api.dependencies import get_current_user
from protean_workspace.models.api import (
    ChatCreateRequest,
    ChatDetailResponse,
    ChatSummaryResponse,
    MessageResponse,
    OpeningPreviewResponse,
    ScenarioResponse,
    SendMessageRequest,
    SendMessageResponse,
)
from protean_workspace.models.domain import User
from protean_workspace.services.chat import (
    CharacterNotFoundError,
    CharacterPhaseNotFoundError,
    CharacterScenarioNotFoundError,
    ChatRequestConflictError,
    ChatServiceError,
    ProviderNotConfiguredError,
)

router = APIRouter(prefix="/api/chats", tags=["chat"])


def _summary(data: dict[str, object]) -> ChatSummaryResponse:
    return ChatSummaryResponse(**data)


@router.post("/opening-preview", response_model=OpeningPreviewResponse)
async def opening_preview(
    request: Request,
    payload: ChatCreateRequest,
    user: User = Depends(get_current_user),
) -> OpeningPreviewResponse:
    try:
        data = await request.app.state.chat_service.preview_opening(
            user.id,
            character_id=payload.character_id,
            phase_id=payload.phase_id,
            scenario_id=payload.scenario_id,
            custom_scenario=payload.custom_scenario.model_dump() if payload.custom_scenario else None,
            tone_id=payload.tone_id,
        )
    except CharacterNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CharacterPhaseNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except CharacterScenarioNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ProviderNotConfiguredError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ChatServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return OpeningPreviewResponse(**data)


@router.post("", response_model=ChatSummaryResponse, status_code=status.HTTP_201_CREATED)
def create_chat(
    request: Request,
    payload: ChatCreateRequest,
    user: User = Depends(get_current_user),
) -> ChatSummaryResponse:
    try:
        data = request.app.state.chat_service.create_chat(
            user.id,
            character_id=payload.character_id,
            phase_id=payload.phase_id,
            scenario_id=payload.scenario_id,
            custom_scenario=payload.custom_scenario.model_dump() if payload.custom_scenario else None,
            tone_id=payload.tone_id,
            title=payload.title,
            opening_token=payload.opening_token,
        )
    except CharacterNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CharacterPhaseNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except CharacterScenarioNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ChatServiceError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _summary(data)


@router.get("", response_model=list[ChatSummaryResponse])
def list_chats(request: Request, user: User = Depends(get_current_user)) -> list[ChatSummaryResponse]:
    return [_summary(item) for item in request.app.state.chat_service.list_chats(user.id)]


@router.get("/{chat_id}", response_model=ChatDetailResponse)
def get_chat(request: Request, chat_id: str, user: User = Depends(get_current_user)) -> ChatDetailResponse:
    try:
        data = request.app.state.chat_service.get_chat(user.id, chat_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found") from exc
    scenario = data.get("scenario")
    return ChatDetailResponse(
        **{key: value for key, value in data.items() if key not in {"messages", "scenario"}},
        scenario=ScenarioResponse(**scenario) if isinstance(scenario, dict) else None,
        messages=[MessageResponse(**item) for item in data["messages"]],
    )


@router.post("/{chat_id}/messages", response_model=SendMessageResponse)
async def send_message(
    request: Request,
    chat_id: str,
    payload: SendMessageRequest,
    user: User = Depends(get_current_user),
) -> SendMessageResponse:
    try:
        data = await request.app.state.chat_service.send_message(
            user.id,
            chat_id,
            payload.message,
            request_id=payload.request_id,
        )
    except ProviderNotConfiguredError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except CharacterNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CharacterPhaseNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except CharacterScenarioNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found") from exc
    except ChatRequestConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ChatServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return SendMessageResponse(**data)
