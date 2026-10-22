from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.adapters.primary.api.logistics_dependencies import (
    create_festival_use_case,
    get_festival_use_case,
    list_festivals_use_case,
)
from app.adapters.primary.api.schemas.festival_schemas import FestivalCreateRequest, FestivalResponse
from app.application.use_cases.logistics.create_festival import CreateFestivalCommand, CreateFestivalUseCase
from app.application.use_cases.logistics.get_festival import GetFestivalUseCase
from app.application.use_cases.logistics.list_festivals import ListFestivalsUseCase
from app.domain.exceptions.logistics_exceptions import FestivalNotFoundError, LogisticsError

# La route de publication reste dans app/api/festivals.py (pôle opérations).
router = APIRouter(prefix="/festivals", tags=["festivals"])


@router.get("", response_model=list[FestivalResponse])
def list_festivals(use_case: Annotated[ListFestivalsUseCase, Depends(list_festivals_use_case)]):
    return [FestivalResponse.from_entity(festival) for festival in use_case.execute()]


@router.post(
    "",
    response_model=FestivalResponse,
    status_code=201,
    responses={400: {"description": "Dates du festival incohérentes"}},
)
def create_festival(
    payload: FestivalCreateRequest,
    use_case: Annotated[CreateFestivalUseCase, Depends(create_festival_use_case)],
):
    command = CreateFestivalCommand(
        name=payload.name,
        location=payload.location,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )
    try:
        festival = use_case.execute(command)
    except LogisticsError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return FestivalResponse.from_entity(festival)


@router.get(
    "/{festival_id}",
    response_model=FestivalResponse,
    responses={404: {"description": "Festival introuvable"}},
)
def get_festival(festival_id: int, use_case: Annotated[GetFestivalUseCase, Depends(get_festival_use_case)]):
    try:
        festival = use_case.execute(festival_id)
    except FestivalNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FestivalResponse.from_entity(festival)
