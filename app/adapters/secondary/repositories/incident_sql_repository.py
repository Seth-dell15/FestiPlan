from sqlalchemy.orm import Session
from app.models import Incident as IncidentModel
from app.domain.models.incident import Incident
from app.domain.ports.repositories.incident_repository_port import IIncidentRepository


class IncidentSqlRepository(IIncidentRepository):
    """Adaptateur de persistance relationnelle SQLAlchemy pour les incidents."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def _to_domain(self, row: IncidentModel) -> Incident:
        return Incident(
            id=row.id,
            concert_id=row.concert_id,
            description=row.description,
            occurred_at=row.occurred_at,
            resolved=row.resolved,
        )

    def save(self, incident: Incident) -> Incident:
        if incident.id is not None:
            # Mise à jour
            row = (
                self.db.query(IncidentModel)
                .filter(IncidentModel.id == incident.id)
                .first()
            )
            if row is not None:
                row.description = incident.description
                row.resolved = incident.resolved
                row.occurred_at = incident.occurred_at
                self.db.commit()
                self.db.refresh(row)
                return self._to_domain(row)

        # Création
        new_row = IncidentModel(
            concert_id=incident.concert_id,
            description=incident.description,
            occurred_at=incident.occurred_at,
            resolved=incident.resolved,
        )
        self.db.add(new_row)
        self.db.commit()
        self.db.refresh(new_row)
        return self._to_domain(new_row)

    def get_by_id(self, incident_id: int) -> Incident | None:
        row = (
            self.db.query(IncidentModel)
            .filter(IncidentModel.id == incident_id)
            .first()
        )
        if row is None:
            return None
        return self._to_domain(row)

    def list_all(self) -> list[Incident]:
        rows = (
            self.db.query(IncidentModel)
            .order_by(IncidentModel.occurred_at.desc())
            .all()
        )
        return [self._to_domain(r) for r in rows]

    def list_by_concert(self, concert_id: int) -> list[Incident]:
        rows = (
            self.db.query(IncidentModel)
            .filter(IncidentModel.concert_id == concert_id)
            .order_by(IncidentModel.occurred_at.desc())
            .all()
        )
        return [self._to_domain(r) for r in rows]
