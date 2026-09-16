from fastapi import APIRouter, Depends, HTTPException, Request, status

from protean_workspace.api.dependencies import get_current_user
from protean_workspace.clients.openrouter import OpenRouterError
from protean_workspace.models.api import (
    PreferencesRequest,
    PreferencesResponse,
    ProviderSettingsRequest,
    ProviderSettingsResponse,
    ProviderValidationResponse,
)
from protean_workspace.models.domain import User
from protean_workspace.services.characters import CharacterLibraryError
from protean_workspace.services.presets import BACKGROUNDS, FRAMES, THEMES, TONES


router = APIRouter(prefix="/api/settings", tags=["settings"])


def _provider_response(request: Request, user_id: int) -> ProviderSettingsResponse:
    prefs = request.app.state.preferences_repository.get(user_id)
    masked = request.app.state.credential_service.masked(user_id, "openrouter")
    return ProviderSettingsResponse(
        configured=masked is not None,
        masked_key=masked,
        model=prefs.provider_model,
        temperature=prefs.temperature,
        target_tokens=prefs.target_tokens,
        max_tokens=prefs.max_tokens,
    )


def _preferences_response(prefs) -> PreferencesResponse:
    return PreferencesResponse(
        library_root=prefs.library_root,
        active_character_id=prefs.active_character_id,
        active_phase_id=prefs.active_phase_id,
        tone_id=prefs.tone_id,
        theme_id=prefs.theme_id,
        background_id=prefs.background_id,
        frame_id=prefs.frame_id,
    )


@router.get("/provider", response_model=ProviderSettingsResponse)
def get_provider_settings(request: Request, user: User = Depends(get_current_user)) -> ProviderSettingsResponse:
    return _provider_response(request, user.id)


@router.put("/provider", response_model=ProviderSettingsResponse)
def update_provider_settings(
    request: Request,
    payload: ProviderSettingsRequest,
    user: User = Depends(get_current_user),
) -> ProviderSettingsResponse:
    current = request.app.state.preferences_repository.get(user.id)
    max_tokens = payload.max_tokens if payload.max_tokens is not None else current.max_tokens
    if payload.target_tokens is not None:
        target_tokens = payload.target_tokens
    else:
        target_tokens = min(current.target_tokens, max_tokens - 128)
    if max_tokens < target_tokens + 128:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hard token ceiling must leave at least 128 tokens of headroom above the target",
        )
    if payload.api_key is not None:
        request.app.state.credential_service.set(user.id, "openrouter", payload.api_key)
    request.app.state.preferences_repository.update(
        user.id,
        provider_model=payload.model,
        temperature=payload.temperature,
        target_tokens=target_tokens,
        max_tokens=payload.max_tokens,
    )
    return _provider_response(request, user.id)


@router.delete("/provider/key", status_code=status.HTTP_204_NO_CONTENT)
def delete_provider_key(request: Request, user: User = Depends(get_current_user)) -> None:
    request.app.state.credential_service.delete(user.id, "openrouter")


@router.post("/provider/validate", response_model=ProviderValidationResponse)
async def validate_provider_key(request: Request, user: User = Depends(get_current_user)) -> ProviderValidationResponse:
    api_key = request.app.state.credential_service.get(user.id, "openrouter")
    if not api_key:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No OpenRouter key is configured")
    try:
        data = await request.app.state.provider_client.validate_key(api_key)
    except OpenRouterError as exc:
        return ProviderValidationResponse(valid=False, detail=str(exc))
    remaining = data.get("limit_remaining")
    return ProviderValidationResponse(
        valid=True,
        label=str(data.get("label")) if data.get("label") is not None else None,
        limit_remaining=float(remaining) if isinstance(remaining, (int, float)) else None,
    )


@router.get("/preferences", response_model=PreferencesResponse)
def get_preferences(request: Request, user: User = Depends(get_current_user)) -> PreferencesResponse:
    return _preferences_response(request.app.state.preferences_repository.get(user.id))


@router.put("/preferences", response_model=PreferencesResponse)
def update_preferences(
    request: Request,
    payload: PreferencesRequest,
    user: User = Depends(get_current_user),
) -> PreferencesResponse:
    current = request.app.state.preferences_repository.get(user.id)
    if payload.library_root is not None:
        try:
            library_root = str(request.app.state.character_library.validate_root(payload.library_root))
        except CharacterLibraryError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    else:
        library_root = None
    effective_root = library_root or current.library_root

    valid_ids = {
        "tone_id": {item.id for item in TONES},
        "theme_id": {item.id for item in THEMES},
        "background_id": {item.id for item in BACKGROUNDS},
        "frame_id": {item.id for item in FRAMES},
    }
    for field, values in valid_ids.items():
        value = getattr(payload, field)
        if value is not None and value not in values:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown {field}: {value}")

    effective_character_id = payload.active_character_id or current.active_character_id
    card = request.app.state.character_library.get(effective_root, effective_character_id)
    if card is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Character '{effective_character_id}' was not found in the configured library",
        )

    if payload.active_character_id is not None and payload.active_phase_id is None:
        phase_id = card.default_phase_id if card.phases else "default"
    elif payload.active_phase_id is not None:
        phase = card.phase(payload.active_phase_id)
        if card.phases and phase.id != payload.active_phase_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown timeline phase '{payload.active_phase_id}' for {card.name}",
            )
        phase_id = phase.id
    else:
        current_phase = current.active_phase_id
        phase = card.phase(current_phase)
        phase_id = phase.id

    prefs = request.app.state.preferences_repository.update(
        user.id,
        library_root=library_root,
        active_character_id=payload.active_character_id,
        active_phase_id=phase_id,
        tone_id=payload.tone_id,
        theme_id=payload.theme_id,
        background_id=payload.background_id,
        frame_id=payload.frame_id,
    )
    return _preferences_response(prefs)
