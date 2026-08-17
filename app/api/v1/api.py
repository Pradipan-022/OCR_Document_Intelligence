from fastapi import APIRouter

from app.api.v1.endpoints import documents

api_router = APIRouter()

# Register the documents endpoints under the "/documents" prefix
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])