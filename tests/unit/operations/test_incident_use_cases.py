from datetime import datetime
import pytest

from app.domain.models.concert import Concert
from app.domain.value_objects.time_slot import TimeSlot
from app.domain.models.incident import Incident
from app.domain.exceptions.scheduling_exceptions import ConcertNotFoundError
from app.domain.exceptions.operation_exceptions import (
    IncidentNotFoundError,
    IncidentInvalidDescriptionError,
    IncidentAlreadyResolvedError,
)
from app.adapters.secondary.repositories.in_memory_concert_repository import (
    InMemoryConcertRepository,
)
from app.adapters.secondary.repositories.in_memory_incident_repository import (
    InMemoryIncidentRepository,
)
from app.application.use_cases.operations.declare_incident import (
    DeclareIncidentUseCase,
    DeclareIncidentCommand,
)
from app.application.use_cases.operations.resolve_incident import (
    ResolveIncidentUseCase,
)
from app.application.use_cases.operations.list_incidents import (
    ListIncidentsUseCase,
)


@pytest.fixture
def existing_concert():
    return Concert(
        id=1,
        festival_id=1,
        artist_id=1,
        stage_id=1,
        time_slot=TimeSlot(
            start=datetime(2027, 6, 18, 14, 0),
            end=datetime(2027, 6, 18, 15, 0),
        ),
    )


def test_declare_incident_with_unknown_concert_raises_error():
    concert_repo = InMemoryConcertRepository()  # vide
    incident_repo = InMemoryIncidentRepository()
    uc = DeclareIncidentUseCase(incident_repo, concert_repo)

    with pytest.raises(ConcertNotFoundError):
        uc.execute(DeclareIncidentCommand(concert_id=99, description="Panne de retour son"))


def test_declare_incident_with_empty_description_raises_r10_error(existing_concert):
    concert_repo = InMemoryConcertRepository([existing_concert])
    incident_repo = InMemoryIncidentRepository()
    uc = DeclareIncidentUseCase(incident_repo, concert_repo)

    with pytest.raises(IncidentInvalidDescriptionError):
        uc.execute(DeclareIncidentCommand(concert_id=1, description="   "))


def test_declare_incident_nominal_success(existing_concert):
    concert_repo = InMemoryConcertRepository([existing_concert])
    incident_repo = InMemoryIncidentRepository()
    uc = DeclareIncidentUseCase(incident_repo, concert_repo)

    incident = uc.execute(
        DeclareIncidentCommand(
            concert_id=1,
            description="Larsen continu sur les retours de scène",
        )
    )

    assert incident.id is not None
    assert incident.concert_id == 1
    assert incident.description == "Larsen continu sur les retours de scène"
    assert incident.resolved is False


def test_resolve_incident_not_found_raises_error():
    incident_repo = InMemoryIncidentRepository()
    uc = ResolveIncidentUseCase(incident_repo)

    with pytest.raises(IncidentNotFoundError):
        uc.execute(incident_id=999)


def test_resolve_incident_success():
    initial_incident = Incident(
        id=1,
        concert_id=1,
        description="Ampli guitare éteint",
        resolved=False,
    )
    incident_repo = InMemoryIncidentRepository([initial_incident])
    uc = ResolveIncidentUseCase(incident_repo)

    resolved = uc.execute(incident_id=1)

    assert resolved.resolved is True
    # Vérifier que c'est bien persisté dans le repo
    in_repo = incident_repo.get_by_id(1)
    assert in_repo is not None
    assert in_repo.resolved is True


def test_list_incidents_filtering():
    inc1 = Incident(id=1, concert_id=1, description="Pb 1", occurred_at=datetime(2027, 6, 18, 14, 10))
    inc2 = Incident(id=2, concert_id=2, description="Pb 2", occurred_at=datetime(2027, 6, 18, 14, 20))
    inc3 = Incident(id=3, concert_id=1, description="Pb 3", occurred_at=datetime(2027, 6, 18, 14, 30))

    repo = InMemoryIncidentRepository([inc1, inc2, inc3])
    uc = ListIncidentsUseCase(repo)

    # Liste complète ordonnée par date décroissante
    all_incidents = uc.execute()
    assert len(all_incidents) == 3
    assert [i.id for i in all_incidents] == [3, 2, 1]

    # Filtré par concert_id=1
    concert_1_incidents = uc.execute(concert_id=1)
    assert len(concert_1_incidents) == 2
    assert [i.id for i in concert_1_incidents] == [3, 1]
