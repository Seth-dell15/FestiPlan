from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import FestivalRead
from app.services.publication_service import PublicationService

router=APIRouter(prefix="/festivals",tags=["festivals"])

@router.post(
    "/{festival_id}/publish",
    response_model=FestivalRead,
    responses={404: {"description": "Festival introuvable"}, 500: {"description": "Échec de la notification"}},
)
def publish_festival(festival_id:int,db:Annotated[Session,Depends(get_db)]):
    try:
        festival=PublicationService(db).publish(festival_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=500,detail=str(exc))
    if festival is None:
        raise HTTPException(status_code=404,detail="Festival introuvable")
    return festival
