import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.db.session import init_db
from app.api.v1.router import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicialización de tablas de base de datos al arrancar la API
    try:
        init_db()
        print("Base de datos e índices inicializados correctamente.")
    except Exception as e:
        print(f"Advertencia al inicializar BD: {e}")

    # Asegurar que existan los directorios de almacenamiento
    os.makedirs(os.path.join(settings.STORAGE_DIR, "uploads"), exist_ok=True)
    os.makedirs(os.path.join(settings.STORAGE_DIR, "extracted"), exist_ok=True)

    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Pipeline Asíncrono de Inteligencia de Documentos con Claim-Check Pattern, Celery, Redis, PostgreSQL y Tesseract OCR.",
    version="1.0.0",
    lifespan=lifespan
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar rutas de API v1
app.include_router(api_router, prefix=settings.API_V1_STR)

# Montar archivos estáticos para la interfaz de usuario
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", include_in_schema=False)
def read_root():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Document Intelligence Async Pipeline API está en ejecución."}

@app.get("/health", tags=["Health Check"])
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "api_version": "v1.0.0"
    }
