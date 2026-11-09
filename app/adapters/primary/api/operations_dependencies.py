"""Assemblage du pôle Opérations : seul endroit où les adaptateurs concrets sont créés et injectés."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.adapters.secondary.notifications.email_notification_adapter import EmailNotificationAdapter
from app.adapters.secondary.repositories.artist_sql_repository import ArtistSqlRepository
from app.adapters.secondary.repositories.concert_sql_repository import ConcertSqlRepository
from app.adapters.secondary.repositories.festival_sql_repository import FestivalSqlRepository
from app.adapters.secondary.repositories.incident_sql_repository import IncidentSqlRepository
from app.adapters.secondary.repositories.stage_sql_repository import StageSqlRepository
from app.application.use_cases.operations.declare_incident import DeclareIncidentUseCase
from app.application.use_cases.operations.list_incidents import ListIncidentsUseCase
from app.application.use_cases.operations.publish_festival import PublishFestivalUseCase
from app.application.use_cases.operations.resolve_incident import ResolveIncidentUseCase
from app.database import get_db

DbSession = Annotated[Session, Depends(get_db)]


def publish_festival_use_case(db: DbSession) -> PublishFestivalUseCase:
    return PublishFestivalUseCase(
        FestivalSqlRepository(db),
        ConcertSqlRepository(db),
        StageSqlRepository(db),
        ArtistSqlRepository(db),
        EmailNotificationAdapter(),
    )


def declare_incident_use_case(db: DbSession) -> DeclareIncidentUseCase:
    return DeclareIncidentUseCase(IncidentSqlRepository(db), ConcertSqlRepository(db))


def list_incidents_use_case(db: DbSession) -> ListIncidentsUseCase:
    return ListIncidentsUseCase(IncidentSqlRepository(db))


def resolve_incident_use_case(db: DbSession) -> ResolveIncidentUseCase:
    return ResolveIncidentUseCase(IncidentSqlRepository(db))
