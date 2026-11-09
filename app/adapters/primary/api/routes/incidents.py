from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.composition import (
    declare_incident_use_case,
    list_incidents_use_case,
    resolve_incident_use_case,
)
from app.adapters.primary.api.schemas.common import EntityId
from app.adapters.primary.api.schemas.incident_schemas import IncidentCreate, IncidentRead
from app.application.ports.inbound import DeclareIncidentCommand, IDeclareIncidentPort
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


@router.post(
    "",
    response_model=IncidentRead,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"description": "Description invalide"}, 404: {"description": "Concert introuvable"}},
)
def create_incident(
    payload: IncidentCreate,
    use_case: Annotated[IDeclareIncidentPort, Depends(declare_incident_use_case)],
):
    command = DeclareIncidentCommand(
        concert_id=payload.concert_id,
        description=payload.description,
        occurred_at=payload.occurred_at,
    )
    try:
        return _to_read_dto(use_case.execute(command))
    except ConcertNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except IncidentInvalidDescriptionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("", response_model=list[IncidentRead])
def list_incidents(
    use_case: Annotated[ListIncidentsUseCase, Depends(list_incidents_use_case)],
    concert_id: EntityId | None = None,
):
    return [_to_read_dto(incident) for incident in use_case.execute(concert_id=concert_id)]


@router.patch(
    "/{incident_id}/resolve",
    response_model=IncidentRead,
    responses={400: {"description": "Incident déjà résolu"}, 404: {"description": "Incident introuvable"}},
)
def resolve_incident(
    incident_id: EntityId,
    use_case: Annotated[ResolveIncidentUseCase, Depends(resolve_incident_use_case)],
):
    try:
        return _to_read_dto(use_case.execute(incident_id=incident_id))
    except IncidentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except IncidentAlreadyResolvedError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
