from datetime import datetime
from typing import get_type_hints

import pytest

from app.adapters.primary.api.routes import concerts, incidents, publication
from app.composition import publish_festival_use_case, reschedule_concert_use_case
from app.application.ports.inbound import (
    IDeclareIncidentPort,
    IPublishFestivalPort,
    IRescheduleConcertPort,
    IScheduleConcertPort,
    IUnpublishFestivalPort,
    PublishFestivalResult,
    RescheduleConcertCommand,
    RescheduleConcertResult,
)
from app.application.use_cases.operations.declare_incident import DeclareIncidentUseCase
from app.application.use_cases.operations.publish_festival import PublishFestivalUseCase
from app.application.use_cases.operations.unpublish_festival import UnpublishFestivalUseCase
from app.application.use_cases.scheduling.reschedule_concert import RescheduleConcertUseCase
from app.application.use_cases.scheduling.schedule_concert import ScheduleConcertUseCase
from app.domain.models.concert import Concert
from app.domain.models.festival import Festival
from app.domain.value_objects.festival_period import FestivalPeriod
from app.domain.value_objects.festival_status import FestivalStatus
from app.domain.value_objects.time_slot import TimeSlot
from app.main import app


@pytest.mark.parametrize(
    "route, port, use_case",
    [
        (concerts.create_concert, IScheduleConcertPort, ScheduleConcertUseCase),
        (concerts.reschedule_concert, IRescheduleConcertPort, RescheduleConcertUseCase),
        (publication.publish_festival, IPublishFestivalPort, PublishFestivalUseCase),
        (publication.unpublish_festival, IUnpublishFestivalPort, UnpublishFestivalUseCase),
        (incidents.create_incident, IDeclareIncidentPort, DeclareIncidentUseCase),
    ],
    ids=["programmer", "deplacer", "publier", "depublier", "declarer_incident"],
)
def test_route_depends_on_the_port_implemented_by_the_use_case(route, port, use_case):
    assert get_type_hints(route, include_extras=True)["use_case"].__origin__ is port
    assert port in use_case.__mro__


@pytest.fixture
def replace_use_case():
    def override(provider, double):
        app.dependency_overrides[provider] = lambda: double

    yield override
    app.dependency_overrides.clear()


class RescheduleDouble(IRescheduleConcertPort):
    def __init__(self):
        self.commands = []

    def execute(self, command: RescheduleConcertCommand) -> RescheduleConcertResult:
        self.commands.append(command)
        concert = Concert(
            id=command.concert_id,
            festival_id=1,
            artist_id=1,
            stage_id=1,
            time_slot=TimeSlot(command.new_start, command.new_end),
        )
        return RescheduleConcertResult(concert=concert, notification_sent=False)


class PublishDouble(IPublishFestivalPort):
    def execute(self, festival_id: int) -> PublishFestivalResult:
        festival = Festival(
            id=festival_id,
            name="Hellforge",
            location="Clisson",
            period=FestivalPeriod(start=datetime(2027, 6, 18, 10), end=datetime(2027, 6, 20, 23)),
            status=FestivalStatus.PUBLISHED,
        )
        return PublishFestivalResult(festival=festival, notification_sent=True)


def test_reschedule_route_works_with_any_port_implementation(client, replace_use_case):
    double = RescheduleDouble()
    replace_use_case(reschedule_concert_use_case, double)

    response = client.patch(
        "/concerts/42/reschedule",
        json={"start_time": "2027-06-18T14:00:00", "end_time": "2027-06-18T15:00:00"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == 42
    assert response.json()["notification_sent"] is False
    assert double.commands == [
        RescheduleConcertCommand(42, datetime(2027, 6, 18, 14), datetime(2027, 6, 18, 15))
    ]


def test_publish_route_works_with_any_port_implementation(client, replace_use_case):
    replace_use_case(publish_festival_use_case, PublishDouble())

    response = client.post("/festivals/7/publish")

    assert response.status_code == 200
    assert response.json()["id"] == 7
    assert response.json()["status"] == "published"
