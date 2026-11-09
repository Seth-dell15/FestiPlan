from dataclasses import replace

from app.adapters.secondary.repositories.in_memory_concert_query_adapter import InMemoryConcertQueryAdapter
from app.domain.models.schedule import Schedule
from app.domain.ports.repositories.festival_repository_port import IFestivalRepository
from app.domain.ports.repositories.schedule_repository_port import IScheduleRepository


class InMemoryScheduleRepository(IScheduleRepository):
    """Implémentation en mémoire du planning, pour les tests sans base de données.

    Le planning est reconstruit à partir des festivals et des concerts en mémoire. Les concerts
    sont copiés au chargement : comme en base, rien n'est modifié tant que `save` n'est pas appelé.
    """

    def __init__(self, festivals: IFestivalRepository, concerts: InMemoryConcertQueryAdapter):
        self._festivals = festivals
        self._concerts = concerts

    def get_by_festival_id(self, festival_id: int) -> Schedule | None:
        festival = self._festivals.get_by_id(festival_id)
        if festival is None:
            return None
        stored = self._concerts.list_for_festival(festival_id, include_cancelled=True)
        return Schedule(
            festival_id=festival_id,
            period=festival.period,
            is_published=festival.is_published,
            concerts=[replace(concert) for concert in stored],
        )

    def get_by_concert_id(self, concert_id: int) -> Schedule | None:
        concert = self._concerts.get_by_id(concert_id)
        return self.get_by_festival_id(concert.festival_id) if concert else None

    def save(self, schedule: Schedule) -> None:
        for concert in schedule.concerts:
            self._concerts.add(concert)
