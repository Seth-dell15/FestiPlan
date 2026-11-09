"""Assemblage du pôle Planification : seul endroit où les adaptateurs concrets
(SQL, notification) sont créés et injectés dans les cas d'utilisation des concerts.

Même principe que logistics_dependencies.py : les routes ne reçoivent que des cas
d'utilisation prêts à l'emploi et ne connaissent ni SQLAlchemy ni l'envoi d'emails.
"""
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.adapters.secondary.repositories.artist_sql_repository import ArtistSqlRepository
from app.adapters.secondary.repositories.concert_sql_repository import ConcertSqlRepository
from app.adapters.secondary.repositories.festival_sql_repository import FestivalSqlQueryAdapter
from app.adapters.secondary.repositories.stage_sql_repository import StageSqlRepository
from app.adapters.secondary.notifications.email_notification_adapter import EmailNotificationAdapter
from app.application.use_cases.scheduling.schedule_concert import ScheduleConcertUseCase
from app.application.use_cases.scheduling.reschedule_concert import RescheduleConcertUseCase
from app.application.use_cases.scheduling.cancel_concert import CancelConcertUseCase
from app.application.use_cases.scheduling.get_schedule import GetFestivalScheduleUseCase
from app.application.use_cases.scheduling.get_concert import GetConcertUseCase

DbSession = Annotated[Session, Depends(get_db)]


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
