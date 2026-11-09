from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.composition import publish_festival_use_case, unpublish_festival_use_case
from app.adapters.primary.api.schemas.festival_schemas import FestivalPublishResponse, FestivalResponse
from app.application.ports.inbound import (
    IPublishFestivalPort,
    IUnpublishFestivalPort,
    PublishFestivalResult,
    UnpublishFestivalResult,
)
from app.domain.exceptions.logistics_exceptions import FestivalNotFoundError
from app.domain.exceptions.operation_exceptions import (
    CannotPublishInvalidScheduleError,
    FestivalAlreadyPublishedError,
    FestivalNotPublishedError,
)

router = APIRouter(prefix="/festivals", tags=["festivals"])


def _to_response(result: PublishFestivalResult | UnpublishFestivalResult) -> FestivalPublishResponse:
    return FestivalPublishResponse(
        **FestivalResponse.from_entity(result.festival).model_dump(),
        notification_sent=result.notification_sent,
    )


@router.post(
    "/{festival_id}/publish",
    response_model=FestivalPublishResponse,
    responses={400: {"description": "Festival déjà publié ou planning invalide"}, 404: {"description": "Festival introuvable"}},
)
def publish_festival(festival_id: int, use_case: Annotated[IPublishFestivalPort, Depends(publish_festival_use_case)]):
    try:
        result = use_case.execute(festival_id)
    except FestivalNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (FestivalAlreadyPublishedError, CannotPublishInvalidScheduleError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_response(result)


@router.post(
    "/{festival_id}/unpublish",
    response_model=FestivalPublishResponse,
    responses={400: {"description": "Festival non publié"}, 404: {"description": "Festival introuvable"}},
)
def unpublish_festival(
    festival_id: int,
    use_case: Annotated[IUnpublishFestivalPort, Depends(unpublish_festival_use_case)],
):
    try:
        result = use_case.execute(festival_id)
    except FestivalNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FestivalNotPublishedError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_response(result)
