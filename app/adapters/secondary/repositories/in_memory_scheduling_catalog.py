from app.domain.ports.repositories.scheduling_catalog_port import (
    ArtistScheduleInfo,
    ISchedulingCatalogPort,
    StageScheduleInfo,
)


class InMemorySchedulingCatalog(ISchedulingCatalogPort):
    """Adaptateur en mémoire du catalogue scènes/artistes, pour les tests des cas d'utilisation."""

    def __init__(
        self,
        stages: list[StageScheduleInfo] | None = None,
        artists: list[ArtistScheduleInfo] | None = None,
    ):
        self._stages = {s.id: s for s in stages or []}
        self._artists = {a.id: a for a in artists or []}

    def get_stage_info(self, stage_id: int) -> StageScheduleInfo | None:
        return self._stages.get(stage_id)

    def get_artist_info(self, artist_id: int) -> ArtistScheduleInfo | None:
        return self._artists.get(artist_id)
