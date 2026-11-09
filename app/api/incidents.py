from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import IncidentCreate, IncidentRead
from app.adapters.secondary.repositories.incident_sql_repository import IncidentSqlRepository
from app.adapters.secondary.repositories.concert_sql_repository import ConcertSqlRepository
from app.application.use_cases.operations.declare_incident import (
    DeclareIncidentUseCase,
    DeclareIncidentCommand,
)
from app.application.use_cases.operations.list_incidents import ListIncidentsUseCase
from app.application.use_cases.operations.resolve_incident import ResolveIncidentUseCase
from app.domain.models.incident import Incident
from app.domain.exceptions.scheduling_exceptions import ConcertNotFoundError
from app.domain.exceptions.operation_exceptions import (
    IncidentNotFoundError,
    IncidentInvalidDescriptionError,
    IncidentAlreadyResolvedError,
)

router = APIRouter(prefix="/incidents", tags=["incidents"])


def _to_read_dto(incident: Incident) -> IncidentRead:
    return IncidentRead(
        id=incident.id or 0,
        concert_id=incident.concert_id,
        description=incident.description,
        occurred_at=incident.occurred_at,
        resolved=incident.resolved,
    )


@router.post("", response_model=IncidentRead, status_code=status.HTTP_201_CREATED)
def create_incident(payload: IncidentCreate, db: Session = Depends(get_db)):
    incident_repo = IncidentSqlRepository(db)
    concert_repo = ConcertSqlRepository(db)
    use_case = DeclareIncidentUseCase(incident_repo, concert_repo)
    try:
        incident = use_case.execute(
            DeclareIncidentCommand(
                concert_id=payload.concert_id,
                description=payload.description,
                occurred_at=payload.occurred_at,
            )
        )
        return _to_read_dto(incident)
    except ConcertNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except IncidentInvalidDescriptionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("", response_model=list[IncidentRead])
def list_incidents(concert_id: int | None = None, db: Session = Depends(get_db)):
    incident_repo = IncidentSqlRepository(db)
    use_case = ListIncidentsUseCase(incident_repo)
    incidents = use_case.execute(concert_id=concert_id)
    return [_to_read_dto(inc) for inc in incidents]


@router.patch("/{incident_id}/resolve", response_model=IncidentRead)
def resolve_incident(incident_id: int, db: Session = Depends(get_db)):
    incident_repo = IncidentSqlRepository(db)
    use_case = ResolveIncidentUseCase(incident_repo)
    try:
        resolved = use_case.execute(incident_id=incident_id)
        return _to_read_dto(resolved)
    except IncidentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except IncidentAlreadyResolvedError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

