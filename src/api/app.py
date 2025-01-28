from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config.settings import settings
from src.core.services.db_service import DatabaseService
from .routes import chat_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create and verify database connection
    db_service = DatabaseService()
    if not await db_service.check_health():
        raise RuntimeError("Failed to connect to database")
    
    yield  # Server is running and handling requests
    
    # Shutdown: Cleanup
    await db_service.close()

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.API_TITLE,
        description=settings.API_DESCRIPTION,
        version=settings.API_VERSION,
        lifespan=lifespan
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Register routers
    app.include_router(chat_router, prefix="/api")
    
    return app

app = create_app()