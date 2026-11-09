from sqlalchemy.orm import Session

from app.domain.models.artist import Artist
from app.domain.ports.repositories.artist_repository_port import IArtistRepository
from app.adapters.secondary.database.models import Artist as ArtistRow
from app.adapters.secondary.repositories.equipment_csv import equipment_from_csv, equipment_to_csv


class ArtistSqlRepository(IArtistRepository):
    """Traduit entre le modèle ORM legacy et l'entité Artist ; les équipements restent stockés en CSV."""

    def __init__(self, session: Session):
        self._session = session

    def get_by_id(self, artist_id: int) -> Artist | None:
        row = self._session.get(ArtistRow, artist_id)
        return _to_entity(row) if row else None

    def list(self) -> list[Artist]:
        rows = self._session.query(ArtistRow).order_by(ArtistRow.name).all()
        return [_to_entity(row) for row in rows]

    def save(self, artist: Artist) -> Artist:
        row = self._session.get(ArtistRow, artist.id) if artist.id else None
        if row is None:
            row = ArtistRow()
            self._session.add(row)
        row.name = artist.name
        row.genre = artist.genre
        row.required_equipment = equipment_to_csv(artist.required_equipment)
        self._session.commit()
        artist.id = row.id
        return artist


def _to_entity(row: ArtistRow) -> Artist:
    return Artist(
        id=row.id,
        name=row.name,
        genre=row.genre,
        required_equipment=equipment_from_csv(row.required_equipment),
    )
