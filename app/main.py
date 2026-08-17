# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.database import Base, engine

# CRITICAL: Import models so SQLAlchemy registers them with Base before table creation
import app.models.document  # noqa: F401


# Lifespan event handler for startup/shutdown tasks
@asynccontextmanager
async def lifespan(app: FastAPI):
    # [TEMP] Auto-create SQLite database tables on server startup for testing
    print("Initializing database and creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Database initialization complete.")
    yield
    # Shutdown logic (if any) goes here


# Initialize FastAPI application with lifespan handler
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for Document Ingestion, Quality Assessment, and OCR Processing",
    version="1.0.0",
    lifespan=lifespan,
)

# 2. Configure CORS (Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins during development
    allow_credentials=True,
    allow_methods=["*"],  # Allows GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],
)


# 3. Global Exception Handler
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


# 4. Health Check Endpoint
@app.get("/", tags=["Health Check"])
async def root():
    """Simple endpoint to verify that the server is running."""
    return {
        "status": "online",
        "project": settings.PROJECT_NAME,
        "message": "Welcome to the Intelligent Document Processing API",
    }


# Mount all V1 API endpoints under /api/v1
app.include_router(api_router, prefix="/api/v1")