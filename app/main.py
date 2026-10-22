from fastapi import FastAPI
from app.config import settings
from app.database import Base,engine
from app import models  # noqa
from app.api import festivals,concerts,incidents
from app.adapters.primary.api.routes import artists,stages
from app.adapters.primary.api.routes import festivals as logistics_festivals

Base.metadata.create_all(bind=engine)
app=FastAPI(title=settings.app_name,version="0.1.0",description="API de gestion d'un festival fictif")

for router in (logistics_festivals.router,festivals.router,artists.router,stages.router,concerts.router,incidents.router): app.include_router(router)

@app.get("/")
def health(): return {"message":"Bienvenue sur FestiPlan","status":"ok"}
