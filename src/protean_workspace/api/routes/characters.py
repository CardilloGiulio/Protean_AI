from fastapi import APIRouter, Depends, HTTPException, Request, status

from protean_workspace.api.dependencies import get_current_user
from protean_workspace.models.api import (
    CharacterPhaseResponse,
    CharacterResearchRequest,
    CharacterResearchResponse,
    CharacterResponse,
    ScenarioResponse,
)
from protean_workspace.models.domain import User
from protean_workspace.services.characters import CharacterLibraryError


router = APIRouter(prefix="/api/characters", tags=["characters"])


def _response(card) -> CharacterResponse:
    return CharacterResponse(
        id=card.id,
        name=card.name,
        franchise=card.franchise,
        description=card.description,
        personality=card.personality,
        scenario=card.scenario,
        first_message=card.first_message,
        tags=list(card.tags),
        source=card.source,
        portrait=card.portrait,
        medium_type=card.medium_type,
        medium_context=card.medium_context,
        story=card.story,
        default_phase_id=card.default_phase_id,
        phases=[
            CharacterPhaseResponse(
                id=phase.id,
                name=phase.name,
                period=phase.period,
                summary=phase.summary,
                first_message=phase.first_message,
                medium_type=phase.medium_type or card.medium_type,
                default_scenario_id=phase.default_scenario_id,
                scenarios=[
                    ScenarioResponse(
                        id=scene.id,
                        name=scene.name,
                        what_happening=scene.what_happening,
                        who_involved=scene.who_involved,
                        dynamic=scene.dynamic,
                        first_message=scene.first_message,
                        custom=scene.custom,
                    )
                    for scene in phase.scenarios
                ],
            )
            for phase in card.phases
        ],
    )


@router.post("/research", response_model=CharacterResearchResponse)
def research_characters(
    request: Request,
    payload: CharacterResearchRequest,
    user: User = Depends(get_current_user),
) -> CharacterResearchResponse:
    prefs = request.app.state.preferences_repository.get(user.id)
    try:
        cards = request.app.state.character_library.research(prefs.library_root, payload.query)
    except CharacterLibraryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return CharacterResearchResponse(root=prefs.library_root, characters=[_response(card) for card in cards])
