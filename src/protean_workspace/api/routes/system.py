from fastapi import APIRouter, Request

from protean_workspace.models.api import (
    AppearancePresetResponse,
    HealthResponse,
    TonePresetResponse,
    UiPresetsResponse,
)
from protean_workspace.services.presets import BACKGROUNDS, FRAMES, THEMES, TONES


router = APIRouter(tags=["system"])


@router.get("/api/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    return HealthResponse(status="ok", version=request.app.state.settings.app_version)


@router.get("/api/ui/presets", response_model=UiPresetsResponse)
def ui_presets() -> UiPresetsResponse:
    return UiPresetsResponse(
        tones=[TonePresetResponse(id=x.id, name=x.name, description=x.description) for x in TONES],
        themes=[AppearancePresetResponse(id=x.id, name=x.name, description=x.description) for x in THEMES],
        backgrounds=[AppearancePresetResponse(id=x.id, name=x.name, description=x.description) for x in BACKGROUNDS],
        frames=[AppearancePresetResponse(id=x.id, name=x.name, description=x.description) for x in FRAMES],
    )
