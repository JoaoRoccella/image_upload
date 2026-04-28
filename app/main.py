"""
Instância principal do FastAPI — configuração de CORS, routers e static files.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import UPLOADS_DIR, init_db
from app.routes import images, sessions

# Garante que a pasta de uploads existe ANTES de montar o StaticFiles
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa o banco de dados e a pasta de uploads ao subir o servidor."""
    init_db()
    yield


app = FastAPI(
    title="Image Upload API",
    description=(
        "API REST para captura e armazenamento de imagens via webcam. "
        "Cada sessão possui um UUID único para recuperar as imagens posteriormente."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — permite o frontend (servido na mesma origem) chamar a API
# Para ambientes de produção, substitua "*" pelo domínio real.
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(sessions.router)
app.include_router(images.router)

# ---------------------------------------------------------------------------
# Servir imagens armazenadas em disco
# ---------------------------------------------------------------------------
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

# ---------------------------------------------------------------------------
# Servir o frontend (pasta static/)
# ---------------------------------------------------------------------------
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
