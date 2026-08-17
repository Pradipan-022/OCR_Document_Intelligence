from fastapi import APIRouter

from app.api.v1.endpoints import document_routes

api_router = APIRouter()

# Register the documents endpoints under the "/documents" prefix
api_router.include_router(document_routes.router, prefix="/documents", tags=["Documents"])