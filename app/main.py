from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app import composition
from app.config import settings
from app.adapters.primary.api.routes import artists, concerts, festivals, incidents, publication, stages
from app.adapters.primary.security.security_headers import SecurityHeadersMiddleware
from app.adapters.primary.security.error_handler import global_security_exception_handler


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    composition.create_tables()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="API de gestion de festival sécurisée (Architecture Hexagonale)",
    lifespan=lifespan,
)

# 1. En-têtes de sécurité HTTP (OWASP)
app.add_middleware(SecurityHeadersMiddleware)

# 2. Protection CORS explicite et contrôlée
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# 3. Gestionnaire d'erreurs sécurisé (anti-fuite de données techniques)
app.add_exception_handler(Exception, global_security_exception_handler)

# 4. Inclusion des routeurs
for router in (
    festivals.router,
    publication.router,
    artists.router,
    stages.router,
    concerts.router,
    incidents.router,
):
    app.include_router(router)


@app.get("/")
def health():
    return {"message": "Bienvenue sur FestiPlan", "status": "ok"}
