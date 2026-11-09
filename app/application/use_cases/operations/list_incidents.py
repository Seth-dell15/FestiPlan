from app.domain.models.incident import Incident
from app.domain.ports.repositories.incident_repository_port import IIncidentRepository


class ListIncidentsUseCase:
    """Cas d'usage : Consultation des incidents signalés."""

    def __init__(self, incident_repo: IIncidentRepository) -> None:
        self.incident_repo = incident_repo

    def execute(self, concert_id: int | None = None) -> list[Incident]:
        if concert_id is not None:
            return self.incident_repo.list_by_concert(concert_id)
        return self.incident_repo.list_all()
