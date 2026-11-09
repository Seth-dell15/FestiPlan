from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.adapters.primary.api.operations_dependencies import publish_festival_use_case
from app.adapters.primary.api.schemas.festival_schemas import FestivalPublishResponse, FestivalResponse
from app.application.use_cases.operations.publish_festival import PublishFestivalUseCase
from app.domain.exceptions.logistics_exceptions import FestivalNotFoundError
from app.domain.exceptions.operation_exceptions import (
    CannotPublishInvalidScheduleError,
    FestivalAlreadyPublishedError,
)

router = APIRouter(prefix="/festivals", tags=["festivals"])


@router.post(
    "/{festival_id}/publish",
    response_model=FestivalPublishResponse,
    responses={400: {"description": "Festival déjà publié ou planning invalide"}, 404: {"description": "Festival introuvable"}},
)
def publish_festival(festival_id: int, use_case: Annotated[PublishFestivalUseCase, Depends(publish_festival_use_case)]):
    try:
        result = use_case.execute(festival_id)
    except FestivalNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (FestivalAlreadyPublishedError, CannotPublishInvalidScheduleError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return FestivalPublishResponse(
        **FestivalResponse.from_entity(result.festival).model_dump(),
        notification_sent=result.notification_sent,
    )
