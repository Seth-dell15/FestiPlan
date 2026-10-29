from app.domain.models.incident import Incident
from app.domain.ports.repositories.incident_repository_port import IIncidentRepository
from app.domain.exceptions.operation_exceptions import IncidentNotFoundError


class ResolveIncidentUseCase:
    """Cas d'usage : Clôture / résolution d'un incident."""

    def __init__(self, incident_repo: IIncidentRepository) -> None:
        self.incident_repo = incident_repo

    def execute(self, incident_id: int) -> Incident:
        incident = self.incident_repo.get_by_id(incident_id)
        if incident is None:
            raise IncidentNotFoundError(f"Incident #{incident_id} introuvable.")

        incident.resolve()
        return self.incident_repo.save(incident)
