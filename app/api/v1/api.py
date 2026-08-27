from fastapi import APIRouter

from app.api.v1.endpoints import document_routes
from app.api.v1.endpoints import auth
from app.api.v1.endpoints import preprocess_routes
from app.api.v1.endpoints import ocr_routes

api_router = APIRouter()

# Register the documents endpoints under the "/documents" prefix
api_router.include_router(
    document_routes.router, 
    prefix="/documents", 
    tags=["Documents"])

api_router.include_router(
    auth.router, 
    prefix="/auth", 
    tags=["Authentication"])

api_router.include_router(
    preprocess_routes.router, 
    prefix="/preprocessing", 
    tags=["Image Preprocessing"]
)

api_router.include_router(
    ocr_routes.router,
    prefix="/ocr",
    tags=["OCR and Extraction"]
)