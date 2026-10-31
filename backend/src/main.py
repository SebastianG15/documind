from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1 import api_v1_router
from src.core.config import settings
from src.schemas.api_schemas import HealthResponse

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Motor de Inteligencia Documental y Cotejo de 3 Vias para Cuentas por Pagar",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Configuracion de CORS para integracion con frontend Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montar routers versionados
app.include_router(api_v1_router, prefix=settings.API_V1_STR)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    """Endpoint de estado del servicio."""
    return HealthResponse(
        status="ok",
        version="1.0.0",
        service=settings.PROJECT_NAME,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
