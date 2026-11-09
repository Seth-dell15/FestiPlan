"""Adaptateur primaire HTTP du pôle Planification (/concerts).

Le contrôleur ne connaît ni SQLAlchemy ni l'envoi de notifications : il reçoit des cas
d'utilisation assemblés dans composition.py, traduit la requête en commande,
puis traduit le résultat ou l'erreur métier en réponse HTTP.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.adapters.primary.api.schemas.concert_schemas import ConcertCreate, ConcertRead, ConcertReschedule, ConcertRescheduleRead
from app import composition as deps
from app.domain.models.concert import Concert
from app.domain.exceptions.scheduling_exceptions import (
    DomainException,
    SchedulingConflictError,
    SchedulingNotFoundError,
)
from app.application.ports.inbound import (
    IRescheduleConcertPort,
    IScheduleConcertPort,
    RescheduleConcertCommand,
    ScheduleConcertCommand,
)
from app.application.use_cases.scheduling.cancel_concert import CancelConcertUseCase
from app.application.use_cases.scheduling.get_schedule import GetFestivalScheduleUseCase
from app.application.use_cases.scheduling.get_concert import GetConcertUseCase

router = APIRouter(prefix="/concerts", tags=["concerts"])


def _to_read_dto(concert: Concert) -> ConcertRead:
    """Mappe l'entité pure du domaine Concert vers le schéma Pydantic de réponse HTTP."""
    return ConcertRead(
        id=concert.id or 0,
        festival_id=concert.festival_id,
        artist_id=concert.artist_id,
        stage_id=concert.stage_id,
        start_time=concert.time_slot.start,
        end_time=concert.time_slot.end,
        status=concert.status.value,
    )


def _to_http_error(exc: Exception) -> HTTPException:
    """Traduction unique des erreurs métier en codes HTTP.

    - 404 : ressource introuvable (concert, festival, scène, artiste)
    - 409 : conflit avec l'état du planning (chevauchement, planning publié, concert annulé)
    - 400 : règle métier violée par les données envoyées (créneau, dates, équipements...)
    """
    if isinstance(exc, SchedulingNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, SchedulingConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("", response_model=list[ConcertRead])
def list_concerts(
    festival_id: int,
    use_case: Annotated[GetFestivalScheduleUseCase, Depends(deps.get_schedule_use_case)],
):
    return [_to_read_dto(c) for c in use_case.execute(festival_id=festival_id)]


@router.get("/{concert_id}", response_model=ConcertRead)
def get_concert(
    concert_id: int,
    use_case: Annotated[GetConcertUseCase, Depends(deps.get_concert_use_case)],
):
    try:
        return _to_read_dto(use_case.execute(concert_id))
    except DomainException as exc:
        raise _to_http_error(exc)


@router.post("", response_model=ConcertRead, status_code=status.HTTP_201_CREATED)
def create_concert(
    payload: ConcertCreate,
    use_case: Annotated[IScheduleConcertPort, Depends(deps.schedule_concert_use_case)],
):
    cmd = ScheduleConcertCommand(
        festival_id=payload.festival_id,
        artist_id=payload.artist_id,
        stage_id=payload.stage_id,
        start_time=payload.start_time,
        end_time=payload.end_time,
    )
    try:
        return _to_read_dto(use_case.execute(cmd))
    except (DomainException, ValueError) as exc:
        raise _to_http_error(exc)


@router.patch("/{concert_id}/reschedule", response_model=ConcertRescheduleRead)
def reschedule_concert(
    concert_id: int,
    payload: ConcertReschedule,
    use_case: Annotated[IRescheduleConcertPort, Depends(deps.reschedule_concert_use_case)],
):
    cmd = RescheduleConcertCommand(
        concert_id=concert_id,
        new_start=payload.start_time,
        new_end=payload.end_time,
    )
    try:
        result = use_case.execute(cmd)
    except (DomainException, ValueError) as exc:
        raise _to_http_error(exc)
    # 200 : le déplacement est enregistré ; notification_sent indique si l'alerte est partie (Défaut 2)
    return ConcertRescheduleRead(
        **_to_read_dto(result.concert).model_dump(),
        notification_sent=result.notification_sent,
    )


@router.post("/{concert_id}/cancel", response_model=ConcertRead)
def cancel_concert(
    concert_id: int,
    use_case: Annotated[CancelConcertUseCase, Depends(deps.cancel_concert_use_case)],
):
    try:
        return _to_read_dto(use_case.execute(concert_id))
    except (DomainException, ValueError) as exc:
        raise _to_http_error(exc)


@router.get("/schedule/{festival_id}", response_model=list[ConcertRead])
def get_schedule(
    festival_id: int,
    use_case: Annotated[GetFestivalScheduleUseCase, Depends(deps.get_schedule_use_case)],
):
    return [_to_read_dto(c) for c in use_case.execute(festival_id)]
