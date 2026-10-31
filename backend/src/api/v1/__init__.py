from fastapi import APIRouter
from src.api.v1.dossiers import router as dossiers_router

api_v1_router = APIRouter()
api_v1_router.include_router(dossiers_router)
