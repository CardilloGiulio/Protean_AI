from fastapi import APIRouter

from protean_workspace.api.routes import assistant, auth, characters, chat, immersion, settings, system


router = APIRouter()
router.include_router(system.router)
router.include_router(auth.router)
router.include_router(settings.router)
router.include_router(characters.router)
router.include_router(chat.router)
router.include_router(immersion.router)
router.include_router(assistant.router)
