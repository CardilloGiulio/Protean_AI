from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from protean_workspace.api.router import router
from protean_workspace.clients.openrouter import OpenRouterClient
from protean_workspace.core.config import Settings, get_settings
from protean_workspace.core.crypto import (
    CredentialCipher,
    load_or_create_fernet_key,
    load_or_create_text_secret,
)
from protean_workspace.db.database import Database
from protean_workspace.db.repositories import (
    ChatRepository,
    CredentialRepository,
    PreferencesRepository,
    SessionRepository,
    UserRepository,
)
from protean_workspace.desktop.launcher import AssistantDesktopLauncher
from protean_workspace.services.assistant import AssistantService
from protean_workspace.services.auth import AuthService
from protean_workspace.services.characters import CharacterLibrary
from protean_workspace.services.chat import ChatService
from protean_workspace.services.context import ContextRepository
from protean_workspace.services.credentials import CredentialService
from protean_workspace.services.immersion import ImmersionService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    settings.instance_dir.mkdir(parents=True, exist_ok=True)

    database = Database(settings.database_path)
    database.initialize()

    jwt_secret = load_or_create_text_secret(settings.jwt_key_path, settings.jwt_secret_key)
    encryption_key = load_or_create_fernet_key(
        settings.encryption_key_path,
        settings.credential_encryption_key,
    )

    users = UserRepository(database)
    sessions = SessionRepository(database)
    sessions.purge_inactive()
    credentials = CredentialRepository(database)
    preferences = PreferencesRepository(database)
    chats = ChatRepository(database)

    character_library = CharacterLibrary(settings)
    context_repository = ContextRepository(settings.context_dir)
    openrouter_client = OpenRouterClient(settings)
    credential_service = CredentialService(credentials, CredentialCipher(encryption_key))
    auth_service = AuthService(
        users=users,
        sessions=sessions,
        preferences=preferences,
        settings=settings,
        jwt_secret=jwt_secret,
    )
    chat_service = ChatService(
        settings=settings,
        chats=chats,
        preferences=preferences,
        credentials=credential_service,
        characters=character_library,
        context=context_repository,
        provider=openrouter_client,
    )
    assistant_service = AssistantService(
        settings=settings,
        preferences=preferences,
        credentials=credential_service,
        characters=character_library,
        provider=openrouter_client,
    )
    assistant_desktop_launcher = AssistantDesktopLauncher(settings.assistant_shell_dir)

    immersion_service = ImmersionService(
        settings=settings,
        preferences=preferences,
        characters=character_library,
        chat_service=chat_service,
    )

    app.state.database = database
    app.state.auth_service = auth_service
    app.state.credential_service = credential_service
    app.state.preferences_repository = preferences
    app.state.character_library = character_library
    app.state.context_repository = context_repository
    app.state.provider_client = openrouter_client
    app.state.chat_service = chat_service
    app.state.immersion_service = immersion_service
    app.state.assistant_service = assistant_service
    app.state.assistant_desktop_launcher = assistant_desktop_launcher

    try:
        yield
    finally:
        assistant_desktop_launcher.shutdown()
        assistant_service.shutdown()
        await openrouter_client.close()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )
    application.state.settings = settings
    application.include_router(router)
    application.mount("/static", StaticFiles(directory=settings.static_dir), name="static")

    @application.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; connect-src 'self'; img-src 'self' data:; "
            "style-src 'self'; script-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
        )
        return response

    @application.middleware("http")
    async def same_origin_write_guard(request: Request, call_next):
        if request.url.path.startswith("/api/") and request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if origin:
                expected = f"{request.url.scheme}://{request.headers.get('host', request.url.netloc)}"
                if origin.rstrip("/") != expected.rstrip("/"):
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={"detail": "Cross-origin state-changing requests are not allowed"},
                    )
        return await call_next(request)

    @application.get("/", include_in_schema=False)
    async def home() -> FileResponse:
        return FileResponse(settings.static_dir / "index.html")

    @application.get("/assistant", include_in_schema=False)
    async def assistant_bridge_page() -> FileResponse:
        return FileResponse(settings.static_dir / "assistant-bridge.html")

    @application.get("/immersion", include_in_schema=False)
    async def immersion_page() -> FileResponse:
        return FileResponse(settings.static_dir / "immersion.html")

    return application


app = create_app()
