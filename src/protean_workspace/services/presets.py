from dataclasses import dataclass


@dataclass(frozen=True)
class TonePreset:
    id: str
    name: str
    description: str
    instruction: str


@dataclass(frozen=True)
class AppearancePreset:
    id: str
    name: str
    description: str


TONES: tuple[TonePreset, ...] = (
    TonePreset("canon", "Canon", "Faithful, restrained characterization.", "Stay close to the character's established temperament, priorities, diction, and limits. Avoid parody or exaggerated catchphrases."),
    TonePreset("immersive", "Immersive", "Atmospheric roleplay with sensory detail.", "Write immersively with concise sensory details, natural dialogue, and scene-aware reactions. Keep momentum and avoid narrating the user's private thoughts."),
    TonePreset("cinematic", "Cinematic", "Dramatic pacing and strong scene beats.", "Use cinematic pacing, visual beats, tension, and decisive dialogue without becoming purple or overlong."),
    TonePreset("intimate", "Intimate", "Quiet, personal, emotionally observant.", "Favor subtle emotional cues, pauses, and personal reactions. Keep the character recognizable rather than universally agreeable."),
    TonePreset("cold", "Cold", "Controlled, analytical, and emotionally distant.", "Use precise, controlled language. Keep emotional expression sparse, observant, and deliberate."),
    TonePreset("playful", "Playful", "Lighter banter and quick reactions.", "Use lively banter, wit, and responsive energy while preserving the character's boundaries and intelligence."),
    TonePreset("narrative", "Narrative", "Balanced prose for longer scenes.", "Blend dialogue with measured third-person scene narration. Maintain continuity and avoid unnecessary recap."),
    TonePreset("tense", "Tense", "Pressure, uncertainty, and clipped reactions.", "Keep tension active through sharper pacing, incomplete certainty, and alert reactions. Do not invent hostility or danger that the selected scenario does not support."),
    TonePreset("vulnerable", "Vulnerable", "Emotionally exposed without forced closeness.", "Allow hesitation, guarded honesty, and emotional cracks when the scenario supports them. Do not manufacture trust, romance, confessions, or knowledge the current relationship has not earned."),
    TonePreset("rivalry", "Rivalry", "Competitive, challenging conversational energy.", "Use challenges, comparison, pride, and competitive banter while preserving the character's actual motives. Rivalry does not automatically imply hatred, friendship, or romance."),
    TonePreset("melancholic", "Melancholic", "Subdued, reflective, and bittersweet.", "Favor quieter pacing, memory, restraint, and the emotional weight of the current timeline while keeping the scene moving and avoiding melodrama."),
    TonePreset("confrontational", "Confrontational", "Direct disagreement and social pressure.", "Let the character challenge claims, push back, accuse, or demand clarity when the scenario supports it. Do not invent physical escalation or an established adversarial relationship."),
)

THEMES: tuple[AppearancePreset, ...] = (
    AppearancePreset("obsidian", "Obsidian", "Dark neutral chrome with warm highlights."),
    AppearancePreset("parchment", "Parchment", "Warm archival paper and aged ink."),
    AppearancePreset("neon", "Neon", "Tokyo-night glass with electric accents."),
    AppearancePreset("amber", "Amber Terminal", "Industrial amber-on-black control surface."),
)

BACKGROUNDS: tuple[AppearancePreset, ...] = (
    AppearancePreset("protean", "Protean", "Dark atmospheric Protean workspace."),
    AppearancePreset("study", "Old Study", "Dark wood, dust, and a quiet desk glow."),
    AppearancePreset("wizard-archive", "Wizard Archive", "Stone archive atmosphere with candle warmth."),
    AppearancePreset("tokyo-rain", "Tokyo Rain", "Rainy metropolitan neon without franchise-specific artwork."),
    AppearancePreset("geofront", "Geofront", "Geometric amber command-center atmosphere."),
    AppearancePreset("void", "Void", "Minimal black gradient for distraction-free chat."),
)

FRAMES: tuple[AppearancePreset, ...] = (
    AppearancePreset("notebook", "Notebook", "Open-page writing surface with an ink-like chat feel."),
    AppearancePreset("tablet", "Tablet", "Modern glass tablet floating above the background."),
    AppearancePreset("terminal", "Terminal", "Dense command-screen frame for technical or EVA-like sessions."),
    AppearancePreset("manuscript", "Manuscript", "Single archival sheet with wide margins."),
)


def get_tone(tone_id: str) -> TonePreset:
    return next((tone for tone in TONES if tone.id == tone_id), TONES[0])
