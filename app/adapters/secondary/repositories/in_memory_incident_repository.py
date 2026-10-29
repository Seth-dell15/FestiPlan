from copy import deepcopy
from app.domain.models.incident import Incident
from app.domain.ports.repositories.incident_repository_port import IIncidentRepository


class InMemoryIncidentRepository(IIncidentRepository):
    """Adaptateur de persistance en mémoire pour les tests unitaires purs."""

    def __init__(self, initial_incidents: list[Incident] | None = None) -> None:
        self._incidents: dict[int, Incident] = {}
        self._auto_id = 1
        if initial_incidents:
            for inc in initial_incidents:
                self.save(inc)

    def save(self, incident: Incident) -> Incident:
        inc_copy = deepcopy(incident)
        if inc_copy.id is None:
            inc_copy.id = self._auto_id
            self._auto_id += 1
        self._incidents[inc_copy.id] = inc_copy
        return deepcopy(inc_copy)

    def get_by_id(self, incident_id: int) -> Incident | None:
        incident = self._incidents.get(incident_id)
        return deepcopy(incident) if incident else None

    def list_all(self) -> list[Incident]:
        sorted_incidents = sorted(
            self._incidents.values(),
            key=lambda x: x.occurred_at,
            reverse=True,
        )
        return [deepcopy(inc) for inc in sorted_incidents]

    def list_by_concert(self, concert_id: int) -> list[Incident]:
        matching = [
            inc for inc in self._incidents.values() if inc.concert_id == concert_id
        ]
        sorted_matching = sorted(
            matching,
            key=lambda x: x.occurred_at,
            reverse=True,
        )
        return [deepcopy(inc) for inc in sorted_matching]
