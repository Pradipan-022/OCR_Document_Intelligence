from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings

from app.api.v1.api import api_router

# Initialize Fast API configuration
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for Document Ingestion, Quality Assessment, and OCR Processing",
    version="1.0.0",
)

# 2. Configure CORS (Cross-Origin Resource Sharing)
# Allows frontends (React, Vue, or web pages) to send HTTP requests to this backend without browser blocking.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins during development
    allow_credentials=True,
    allow_methods=["*"],  # Allows GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],
)

# 3. Global Exception Handler
# Automatically catches any `ValueError` raised by services (e.g., invalid file types or oversized files)
# and converts it into a clean HTTP 400 Bad Request response.
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