from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import ConcertCreate, ConcertRead, ConcertReschedule
from app.domain.models.concert import Concert
from app.domain.exceptions.scheduling_exceptions import (
    DomainException,
    ConcertNotFoundError,
)
from app.adapters.secondary.repositories.concert_sql_repository import ConcertSqlRepository
from app.adapters.secondary.repositories.festival_sql_repository import FestivalSqlQueryAdapter
from app.adapters.secondary.notifications.email_notification_adapter import EmailNotificationAdapter
from app.application.use_cases.scheduling.reschedule_concert import (
    RescheduleConcertUseCase,
    RescheduleConcertCommand,
)
from app.application.use_cases.scheduling.schedule_concert import (
    ScheduleConcertUseCase,
    ScheduleConcertCommand,
)
from app.application.use_cases.scheduling.cancel_concert import CancelConcertUseCase
from app.application.use_cases.scheduling.get_schedule import GetFestivalScheduleUseCase

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
        status=concert.status,
    )


def _get_dependencies(db: Session = Depends(get_db)):
    """Module de composition des dépendances hexagonales pour les requêtes HTTP."""
    concert_repo = ConcertSqlRepository(db)
    festival_port = FestivalSqlQueryAdapter(db)
    notification_sender = EmailNotificationAdapter()
    return concert_repo, festival_port, notification_sender


@router.get("", response_model=list[ConcertRead])
def list_concerts(festival_id: int, deps=Depends(_get_dependencies)):
    concert_repo, _, _ = deps
    use_case = GetFestivalScheduleUseCase(concert_repo)
    concerts = use_case.execute(festival_id=festival_id)
    return [_to_read_dto(c) for c in concerts]


@router.get("/{concert_id}", response_model=ConcertRead)
def get_concert(concert_id: int, deps=Depends(_get_dependencies)):
    concert_repo, _, _ = deps
    concert = concert_repo.get_by_id(concert_id)
    if concert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Concert introuvable",
        )
    return _to_read_dto(concert)


@router.post("", response_model=ConcertRead, status_code=status.HTTP_201_CREATED)
def create_concert(payload: ConcertCreate, deps=Depends(_get_dependencies)):
    concert_repo, festival_port, _ = deps
    use_case = ScheduleConcertUseCase(
        concert_repository=concert_repo,
        festival_query_port=festival_port,
    )
    cmd = ScheduleConcertCommand(
        festival_id=payload.festival_id,
        artist_id=payload.artist_id,
        stage_id=payload.stage_id,
        start_time=payload.start_time,
        end_time=payload.end_time,
    )
    try:
        concert = use_case.execute(cmd)
        return _to_read_dto(concert)
    except (DomainException, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.patch("/{concert_id}/reschedule", response_model=ConcertRead)
def reschedule_concert(
    concert_id: int,
    payload: ConcertReschedule,
    deps=Depends(_get_dependencies),
):
    concert_repo, festival_port, notification_sender = deps
    use_case = RescheduleConcertUseCase(
        concert_repository=concert_repo,
        festival_query_port=festival_port,
        notification_sender=notification_sender,
    )
    cmd = RescheduleConcertCommand(
        concert_id=concert_id,
        new_start=payload.start_time,
        new_end=payload.end_time,
    )
    try:
        result = use_case.execute(cmd)
        return _to_read_dto(result.concert)
    except ConcertNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Concert introuvable",
        )
    except DomainException as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/{concert_id}/cancel", response_model=ConcertRead)
def cancel_concert(concert_id: int, deps=Depends(_get_dependencies)):
    concert_repo, _, _ = deps
    use_case = CancelConcertUseCase(concert_repo)
    try:
        cancelled = use_case.execute(concert_id)
        return _to_read_dto(cancelled)
    except ConcertNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Concert introuvable",
        )


@router.get("/schedule/{festival_id}", response_model=list[ConcertRead])
def get_schedule(festival_id: int, deps=Depends(_get_dependencies)):
    concert_repo, _, _ = deps
    use_case = GetFestivalScheduleUseCase(concert_repo)
    return [_to_read_dto(c) for c in use_case.execute(festival_id)]
