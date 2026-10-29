from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Festival
from app.schemas import FestivalCreate, FestivalRead
from app.services.festival_service import FestivalService
from app.adapters.secondary.repositories.festival_sql_repository import FestivalSqlQueryAdapter
from app.adapters.secondary.repositories.concert_sql_repository import ConcertSqlRepository
from app.adapters.secondary.notifications.email_notification_adapter import EmailNotificationAdapter
from app.application.use_cases.operations.publish_festival import PublishFestivalUseCase
from app.domain.exceptions.operation_exceptions import (
    FestivalNotFoundError,
    FestivalAlreadyPublishedError,
    CannotPublishInvalidScheduleError,
)

router=APIRouter(prefix="/festivals",tags=["festivals"])

@router.get("",response_model=list[FestivalRead])
def list_festivals(db:Session=Depends(get_db)): 
    return FestivalService(db).list_festivals()

@router.post("",response_model=FestivalRead,status_code=201)
def create_festival(payload:FestivalCreate,db:Session=Depends(get_db)):
    try:
        return FestivalService(db).create_festival(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc))

@router.post("/{festival_id}/publish",response_model=FestivalRead)
def publish_festival(festival_id:int,db:Session=Depends(get_db)):
    festival_adapter = FestivalSqlQueryAdapter(db)
    concert_repo = ConcertSqlRepository(db)
    notification_sender = EmailNotificationAdapter()
    use_case = PublishFestivalUseCase(
        festival_query=festival_adapter,
        festival_cmd=festival_adapter,
        concert_repo=concert_repo,
        notification_sender=notification_sender,
    )
    try:
        use_case.execute(festival_id)
    except FestivalNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except (FestivalAlreadyPublishedError, CannotPublishInvalidScheduleError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    festival = db.query(Festival).filter(Festival.id == festival_id).first()
    if festival is None:
        raise HTTPException(status_code=404, detail="Festival introuvable")
    return festival

