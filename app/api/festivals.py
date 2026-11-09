from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.adapters.primary.api.logistics_dependencies import get_festival_use_case
from app.adapters.primary.api.schemas.festival_schemas import FestivalResponse
from app.adapters.secondary.repositories.festival_sql_repository import FestivalSqlQueryAdapter
from app.adapters.secondary.repositories.concert_sql_repository import ConcertSqlRepository
from app.adapters.secondary.notifications.email_notification_adapter import EmailNotificationAdapter
from app.application.use_cases.logistics.get_festival import GetFestivalUseCase
from app.application.use_cases.operations.publish_festival import PublishFestivalUseCase
from app.domain.exceptions.operation_exceptions import (
    FestivalNotFoundError,
    FestivalAlreadyPublishedError,
    CannotPublishInvalidScheduleError,
)

router=APIRouter(prefix="/festivals",tags=["festivals"])

@router.post(
    "/{festival_id}/publish",
    response_model=FestivalResponse,
    responses={400: {"description": "Festival déjà publié ou planning invalide"}, 404: {"description": "Festival introuvable"}},
)
def publish_festival(
    festival_id:int,
    db:Annotated[Session,Depends(get_db)],
    get_festival:Annotated[GetFestivalUseCase,Depends(get_festival_use_case)],
):
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

    return FestivalResponse.from_entity(get_festival.execute(festival_id))
