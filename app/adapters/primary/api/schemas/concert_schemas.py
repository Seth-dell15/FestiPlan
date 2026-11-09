from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.adapters.primary.api.schemas.common import EntityId


class ConcertCreate(BaseModel):
    festival_id: EntityId
    artist_id: EntityId
    stage_id: EntityId
    start_time: datetime
    end_time: datetime


class ConcertReschedule(BaseModel):
    start_time: datetime
    end_time: datetime


class ConcertRead(BaseModel):
    id: int
    festival_id: int
    artist_id: int
    stage_id: int
    start_time: datetime
    end_time: datetime
    status: str
    model_config = ConfigDict(from_attributes=True)


class ConcertRescheduleRead(ConcertRead):
    """Réponse du déplacement : le concert déplacé + l'état de la notification (Défaut 2).

    Le déplacement est enregistré même si notification_sent vaut False.
    """
    notification_sent: bool
