"""Point de composition : seul module qui crée les adaptateurs concrets et les injecte dans les cas d'usage."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.adapters.secondary.database import models  # noqa: F401  enregistre les tables dans Base.metadata
from app.adapters.secondary.database.session import Base, engine, get_db
from app.adapters.secondary.notifications.email_notification_adapter import EmailNotificationAdapter
from app.adapters.secondary.repositories.artist_sql_repository import ArtistSqlRepository
from app.adapters.secondary.repositories.concert_sql_repository import ConcertSqlRepository
from app.adapters.secondary.repositories.festival_sql_repository import FestivalSqlQueryAdapter, FestivalSqlRepository
from app.adapters.secondary.repositories.incident_sql_repository import IncidentSqlRepository
from app.adapters.secondary.repositories.stage_sql_repository import StageSqlRepository
from app.application.use_cases.logistics.create_artist import CreateArtistUseCase
from app.application.use_cases.logistics.create_festival import CreateFestivalUseCase
from app.application.use_cases.logistics.create_stage import CreateStageUseCase
from app.application.use_cases.logistics.get_festival import GetFestivalUseCase
from app.application.use_cases.logistics.list_artists import ListArtistsUseCase
from app.application.use_cases.logistics.list_festivals import ListFestivalsUseCase
from app.application.use_cases.logistics.list_stages import ListStagesUseCase
from app.application.use_cases.operations.declare_incident import DeclareIncidentUseCase
from app.application.use_cases.operations.list_incidents import ListIncidentsUseCase
from app.application.use_cases.operations.publish_festival import PublishFestivalUseCase
from app.application.use_cases.operations.resolve_incident import ResolveIncidentUseCase
from app.application.use_cases.scheduling.cancel_concert import CancelConcertUseCase
from app.application.use_cases.scheduling.get_concert import GetConcertUseCase
from app.application.use_cases.scheduling.get_schedule import GetFestivalScheduleUseCase
from app.application.use_cases.scheduling.reschedule_concert import RescheduleConcertUseCase
from app.application.use_cases.scheduling.schedule_concert import ScheduleConcertUseCase

DbSession = Annotated[Session, Depends(get_db)]


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


def create_festival_use_case(db: DbSession) -> CreateFestivalUseCase:
    return CreateFestivalUseCase(FestivalSqlRepository(db))


def list_festivals_use_case(db: DbSession) -> ListFestivalsUseCase:
    return ListFestivalsUseCase(FestivalSqlRepository(db))


def get_festival_use_case(db: DbSession) -> GetFestivalUseCase:
    return GetFestivalUseCase(FestivalSqlRepository(db))


def create_artist_use_case(db: DbSession) -> CreateArtistUseCase:
    return CreateArtistUseCase(ArtistSqlRepository(db))


def list_artists_use_case(db: DbSession) -> ListArtistsUseCase:
    return ListArtistsUseCase(ArtistSqlRepository(db))


def create_stage_use_case(db: DbSession) -> CreateStageUseCase:
    return CreateStageUseCase(StageSqlRepository(db), FestivalSqlRepository(db))


def list_stages_use_case(db: DbSession) -> ListStagesUseCase:
    return ListStagesUseCase(StageSqlRepository(db))


def schedule_concert_use_case(db: DbSession) -> ScheduleConcertUseCase:
    return ScheduleConcertUseCase(
        ConcertSqlRepository(db), FestivalSqlQueryAdapter(db), StageSqlRepository(db), ArtistSqlRepository(db)
    )


def reschedule_concert_use_case(db: DbSession) -> RescheduleConcertUseCase:
    return RescheduleConcertUseCase(
        ConcertSqlRepository(db), FestivalSqlQueryAdapter(db), EmailNotificationAdapter()
    )


def cancel_concert_use_case(db: DbSession) -> CancelConcertUseCase:
    return CancelConcertUseCase(ConcertSqlRepository(db), FestivalSqlQueryAdapter(db))


def get_schedule_use_case(db: DbSession) -> GetFestivalScheduleUseCase:
    return GetFestivalScheduleUseCase(ConcertSqlRepository(db))


def get_concert_use_case(db: DbSession) -> GetConcertUseCase:
    return GetConcertUseCase(ConcertSqlRepository(db))


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
