from datetime import datetime
import pytest
from app.domain.models.incident import Incident
from app.domain.exceptions.operation_exceptions import (
    IncidentInvalidDescriptionError,
    IncidentAlreadyResolvedError,
)
from app.domain.events.operation_events import IncidentResolvedEvent


def test_valid_incident_creation():
    now = datetime(2027, 6, 18, 20, 15)
    incident = Incident(
        concert_id=1,
        description="Micro défectueux sur scène",
        occurred_at=now,
        id=10,
    )
    assert incident.concert_id == 1
    assert incident.description == "Micro défectueux sur scène"
    assert incident.occurred_at == now
    assert incident.resolved is False
    assert incident.id == 10


def test_incident_description_is_stripped():
    incident = Incident(
        concert_id=1,
        description="   Coupure de son partielle   ",
    )
    assert incident.description == "Coupure de son partielle"


@pytest.mark.parametrize("empty_desc", ["", "   ", "\t\n"])
def test_empty_description_raises_r10_error(empty_desc):
    with pytest.raises(IncidentInvalidDescriptionError, match="ne peut pas être vide"):
        Incident(concert_id=1, description=empty_desc)


def test_invalid_concert_id_raises_error():
    with pytest.raises(IncidentInvalidDescriptionError, match="rattaché à un concert"):
        Incident(concert_id=0, description="Ampli en feu")


def test_resolve_incident_success():
    incident = Incident(concert_id=1, description="Câble XLR sectionné", id=42)
    assert incident.resolved is False

    event = incident.resolve()

    assert incident.resolved is True
    assert isinstance(event, IncidentResolvedEvent)
    assert event.incident_id == 42


def test_resolve_already_resolved_incident_raises_error():
    incident = Incident(concert_id=1, description="Câble XLR sectionné", id=42)
    incident.resolve()

    with pytest.raises(IncidentAlreadyResolvedError):
        incident.resolve()
