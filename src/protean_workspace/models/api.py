from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    version: str


class AuthStatusResponse(BaseModel):
    initialized: bool
    authenticated: bool
    username: str | None = None


class AuthRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=10, max_length=256)


class UserResponse(BaseModel):
    id: int
    username: str


class ProviderSettingsRequest(BaseModel):
    api_key: str | None = Field(default=None, min_length=8, max_length=4096)
    model: str | None = Field(default=None, min_length=1, max_length=200)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    target_tokens: int | None = Field(default=None, ge=64, le=8192)
    max_tokens: int | None = Field(default=None, ge=128, le=32768)


class ProviderSettingsResponse(BaseModel):
    provider: str = "openrouter"
    configured: bool
    masked_key: str | None = None
    model: str
    temperature: float
    target_tokens: int
    max_tokens: int


class ProviderValidationResponse(BaseModel):
    valid: bool
    label: str | None = None
    limit_remaining: float | None = None
    detail: str | None = None


class PreferencesRequest(BaseModel):
    library_root: str | None = Field(default=None, max_length=2048)
    active_character_id: str | None = Field(default=None, max_length=200)
    active_phase_id: str | None = Field(default=None, max_length=200)
    tone_id: str | None = Field(default=None, max_length=100)
    theme_id: str | None = Field(default=None, max_length=100)
    background_id: str | None = Field(default=None, max_length=100)
    frame_id: str | None = Field(default=None, max_length=100)


class PreferencesResponse(BaseModel):
    library_root: str
    active_character_id: str
    active_phase_id: str
    tone_id: str
    theme_id: str
    background_id: str
    frame_id: str


class ScenarioInput(BaseModel):
    name: str = Field(default="Custom scene", min_length=1, max_length=120)
    what_happening: str = Field(min_length=1, max_length=3000)
    who_involved: str = Field(min_length=1, max_length=1200)
    dynamic: str = Field(min_length=1, max_length=2000)


class ScenarioResponse(BaseModel):
    id: str
    name: str
    what_happening: str
    who_involved: str
    dynamic: str
    first_message: str = ""
    custom: bool = False


class CharacterPhaseResponse(BaseModel):
    id: str
    name: str
    period: str
    summary: str
    first_message: str = ""
    medium_type: str = "chat"
    default_scenario_id: str = ""
    scenarios: list[ScenarioResponse] = []


class CharacterResponse(BaseModel):
    id: str
    name: str
    franchise: str
    description: str
    personality: str
    scenario: str
    first_message: str
    tags: list[str]
    source: str
    portrait: str = ""
    medium_type: str = "chat"
    medium_context: str = ""
    story: str = ""
    default_phase_id: str = "default"
    phases: list[CharacterPhaseResponse] = []


class CharacterResearchRequest(BaseModel):
    query: str = Field(default="", max_length=200)


class CharacterResearchResponse(BaseModel):
    root: str
    characters: list[CharacterResponse]


class TonePresetResponse(BaseModel):
    id: str
    name: str
    description: str


class AppearancePresetResponse(BaseModel):
    id: str
    name: str
    description: str


class UiPresetsResponse(BaseModel):
    tones: list[TonePresetResponse]
    themes: list[AppearancePresetResponse]
    backgrounds: list[AppearancePresetResponse]
    frames: list[AppearancePresetResponse]


class ChatCreateRequest(BaseModel):
    character_id: str | None = Field(default=None, max_length=200)
    phase_id: str | None = Field(default=None, max_length=200)
    scenario_id: str | None = Field(default=None, max_length=200)
    custom_scenario: ScenarioInput | None = None
    tone_id: str | None = Field(default=None, max_length=100)
    title: str | None = Field(default=None, max_length=160)
    opening_token: str | None = Field(default=None, max_length=200)


class OpeningPreviewResponse(BaseModel):
    message: str
    opening_token: str
    character_id: str
    phase_id: str
    scenario_id: str
    tone_id: str
    medium_type: str


class ChatSummaryResponse(BaseModel):
    id: str
    title: str
    character_id: str
    phase_id: str
    scenario_id: str
    scenario_name: str
    tone_id: str
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime


class ChatDetailResponse(ChatSummaryResponse):
    scenario: ScenarioResponse | None = None
    messages: list[MessageResponse]


class SendMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20000)
    request_id: str = Field(
        default_factory=lambda: uuid4().hex,
        min_length=16,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    )


class SendMessageResponse(BaseModel):
    chat_id: str
    request_id: str
    reply: str
    character_id: str
    phase_id: str
    scenario_id: str
    tone_id: str


class ImmersionPhaseOption(BaseModel):
    id: str
    name: str
    period: str
    render_mode: str
    sprite_pack_id: str
    default_background_id: str
    default_background_path: str


class ImmersionCharacterOption(BaseModel):
    character_id: str
    name: str
    portrait: str = ""
    phases: list[ImmersionPhaseOption] = []


class ImmersionAvailabilityResponse(BaseModel):
    enabled: bool
    characters: list[ImmersionCharacterOption] = []


class ImmersionPresentationResponse(BaseModel):
    render_mode: str
    sprite_pack_id: str
    expression: str
    sprite_path: str | None = None
    movement: str
    location: str
    location_changed: bool = False
    background_id: str
    background_path: str


class ImmersionStartRequest(BaseModel):
    character_id: str = Field(min_length=1, max_length=200)
    phase_id: str = Field(min_length=1, max_length=200)
    scenario_id: str | None = Field(default=None, max_length=200)
    custom_scenario: ScenarioInput | None = None
    tone_id: str = Field(min_length=1, max_length=100)


class ImmersionStartResponse(BaseModel):
    chat: ChatSummaryResponse
    character_name: str
    phase_name: str
    scenario_name: str
    tone_name: str
    opening: str
    presentation: ImmersionPresentationResponse


class ImmersionMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20000)
    request_id: str = Field(
        default_factory=lambda: uuid4().hex,
        min_length=16,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    current_background_id: str | None = Field(default=None, max_length=200)
    current_location: str | None = Field(default=None, max_length=240)


class ImmersionMessageResponse(BaseModel):
    chat_id: str
    request_id: str
    reply: str
    character_id: str
    phase_id: str
    scenario_id: str
    tone_id: str
    presentation: ImmersionPresentationResponse


class AssistantPhaseOption(BaseModel):
    id: str
    name: str
    period: str


class AssistantWardrobeOption(BaseModel):
    id: str
    label: str
    status: str
    lock_reason: str = ""


class AssistantCharacterOption(BaseModel):
    character_id: str
    name: str
    portrait: str = ""
    default_wardrobe_id: str
    phases: list[AssistantPhaseOption] = []
    wardrobes: list[AssistantWardrobeOption] = []


class AssistantAvailabilityResponse(BaseModel):
    enabled: bool
    characters: list[AssistantCharacterOption] = []


class AssistantStartRequest(BaseModel):
    character_id: str = Field(min_length=1, max_length=200)
    phase_id: str = Field(min_length=1, max_length=200)
    scenario_id: str | None = Field(default=None, max_length=200)
    custom_scenario: ScenarioInput | None = None
    tone_id: str = Field(min_length=1, max_length=100)
    wardrobe_id: str = Field(min_length=1, max_length=100)
    background_mode: str = Field(default="transparent", pattern=r"^(transparent|protean|custom)$")
    custom_background_data_url: str | None = Field(default=None, max_length=9_000_000)
    custom_background_name: str | None = Field(default=None, max_length=255)


class AssistantStartResponse(BaseModel):
    launched: bool
    character_name: str
    phase_name: str
    scenario_name: str
    tone_name: str
    wardrobe_label: str
    bridge_url: str = "/assistant"


class AssistantSessionResponse(BaseModel):
    character_id: str
    character_name: str
    phase_id: str
    phase_name: str
    scenario_id: str
    scenario_name: str
    tone_id: str
    tone_name: str
    wardrobe_id: str
    wardrobe_label: str
    wardrobes: list[AssistantWardrobeOption] = []
    expressions: list[str] = []
    sprite_paths: dict[str, str] = {}
    background_mode: str
    has_custom_background: bool = False
    screen_enabled: bool = False


class AssistantScreenContext(BaseModel):
    application: str = Field(default="", max_length=200)
    window_title: str = Field(default="", max_length=1000)
    image_data_url: str = Field(default="", max_length=2_500_000)


class AssistantEventRequest(BaseModel):
    event_type: str = Field(
        pattern=r"^(launch|idle_observation|menu_open|search_open|interact_open|poke|search|interact|wardrobe_open|wardrobe_change|quit|screen_toggle)$"
    )
    input_type: str | None = Field(default=None, pattern=r"^(speech|dev)$")
    text: str | None = Field(default=None, max_length=5000)
    query: str | None = Field(default=None, max_length=1000)
    poke_count: int | None = Field(default=None, ge=2, le=50)
    old_wardrobe_id: str | None = Field(default=None, max_length=100)
    new_wardrobe_id: str | None = Field(default=None, max_length=100)
    screen: AssistantScreenContext | None = None


class AssistantEventResponse(BaseModel):
    reaction: str
    remark: str
    wardrobe_id: str
    wardrobe_label: str
    sprite_paths: dict[str, str] = {}


class AssistantWardrobeChangeRequest(BaseModel):
    wardrobe_id: str = Field(min_length=1, max_length=100)


class AssistantWardrobeChangeResponse(BaseModel):
    old_wardrobe_id: str
    wardrobe_id: str
    wardrobe_label: str
    sprite_paths: dict[str, str] = {}


class AssistantCloseResponse(BaseModel):
    closed: bool = True
