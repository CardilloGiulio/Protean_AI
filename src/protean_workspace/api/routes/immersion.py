from fastapi import APIRouter, Depends, HTTPException, Request, status

from protean_workspace.api.dependencies import get_current_user
from protean_workspace.models.api import (
    ImmersionAvailabilityResponse,
    ImmersionMessageRequest,
    ImmersionMessageResponse,
    ImmersionStartRequest,
    ImmersionStartResponse,
)
from protean_workspace.models.domain import User
from protean_workspace.services.chat import (
    CharacterNotFoundError,
    CharacterPhaseNotFoundError,
    CharacterScenarioNotFoundError,
    ChatServiceError,
    ProviderNotConfiguredError,
)
from protean_workspace.services.immersion import ImmersionUnavailableError

router = APIRouter(prefix="/api/immersion", tags=["immersion"])


@router.get("/availability", response_model=ImmersionAvailabilityResponse)
def availability(request: Request, user: User = Depends(get_current_user)) -> ImmersionAvailabilityResponse:
    return ImmersionAvailabilityResponse(**request.app.state.immersion_service.availability(user.id))


@router.post("/start", response_model=ImmersionStartResponse, status_code=status.HTTP_201_CREATED)
async def start_immersion(
    request: Request,
    payload: ImmersionStartRequest,
    user: User = Depends(get_current_user),
) -> ImmersionStartResponse:
    try:
        result = await request.app.state.immersion_service.start(
            user.id,
            character_id=payload.character_id,
            phase_id=payload.phase_id,
            scenario_id=payload.scenario_id,
            custom_scenario=payload.custom_scenario.model_dump() if payload.custom_scenario else None,
            tone_id=payload.tone_id,
        )
    except ImmersionUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ProviderNotConfiguredError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except CharacterNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (CharacterPhaseNotFoundError, CharacterScenarioNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ChatServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return ImmersionStartResponse(**result)


@router.post("/{chat_id}/messages", response_model=ImmersionMessageResponse)
async def send_immersion_message(
    request: Request,
    chat_id: str,
    payload: ImmersionMessageRequest,
    user: User = Depends(get_current_user),
) -> ImmersionMessageResponse:
    try:
        result = await request.app.state.immersion_service.send_message(
            user.id,
            chat_id,
            message=payload.message,
            request_id=payload.request_id,
            current_background_id=payload.current_background_id,
            current_location=payload.current_location,
        )
    except ImmersionUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ProviderNotConfiguredError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except (CharacterNotFoundError, LookupError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Immersion chat not found") from exc
    except (CharacterPhaseNotFoundError, CharacterScenarioNotFoundError, ChatServiceError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ImmersionMessageResponse(**result)
