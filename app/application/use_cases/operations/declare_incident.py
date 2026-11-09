from datetime import datetime, timezone
from app.application.ports.inbound import DeclareIncidentCommand, IDeclareIncidentPort
from app.domain.models.incident import Incident
from app.domain.ports.repositories.incident_repository_port import IIncidentRepository
from app.domain.ports.repositories.concert_query_port import IConcertQueryPort
from app.domain.exceptions.scheduling_exceptions import ConcertNotFoundError


class DeclareIncidentUseCase(IDeclareIncidentPort):
    """Cas d'usage : Signalement d'un incident survenu lors d'un concert (R10)."""

    def __init__(
        self,
        incident_repo: IIncidentRepository,
        concert_repo: IConcertQueryPort,
    ) -> None:
        self.incident_repo = incident_repo
        self.concert_repo = concert_repo

    def execute(self, command: DeclareIncidentCommand) -> Incident:
        # Vérifier que le concert existe
        concert = self.concert_repo.get_by_id(command.concert_id)
        if concert is None:
            raise ConcertNotFoundError(command.concert_id)

        incident = Incident(
            concert_id=command.concert_id,
            description=command.description,
            occurred_at=command.occurred_at or datetime.now(timezone.utc).replace(tzinfo=None),
        )

        return self.incident_repo.save(incident)
