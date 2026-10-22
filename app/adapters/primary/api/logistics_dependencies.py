"""Assemblage du pôle logistique : seul endroit où les repositories SQL sont créés et injectés dans les use cases."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.adapters.secondary.repositories.artist_sql_repository import ArtistSqlRepository
from app.adapters.secondary.repositories.festival_sql_repository import FestivalSqlRepository
from app.adapters.secondary.repositories.stage_sql_repository import StageSqlRepository
from app.application.use_cases.logistics.create_artist import CreateArtistUseCase
from app.application.use_cases.logistics.create_stage import CreateStageUseCase
from app.application.use_cases.logistics.list_artists import ListArtistsUseCase
from app.application.use_cases.logistics.list_stages import ListStagesUseCase
from app.database import get_db

DbSession = Annotated[Session, Depends(get_db)]


def create_artist_use_case(db: DbSession) -> CreateArtistUseCase:
    return CreateArtistUseCase(ArtistSqlRepository(db))


def list_artists_use_case(db: DbSession) -> ListArtistsUseCase:
    return ListArtistsUseCase(ArtistSqlRepository(db))


def create_stage_use_case(db: DbSession) -> CreateStageUseCase:
    return CreateStageUseCase(StageSqlRepository(db), FestivalSqlRepository(db))


def list_stages_use_case(db: DbSession) -> ListStagesUseCase:
    return ListStagesUseCase(StageSqlRepository(db))
