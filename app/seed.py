"""Réinitialise la base configurée et charge le jeu de données de démonstration."""
from datetime import datetime

from app.adapters.secondary.database.models import Artist, Concert, Festival, Incident, Stage
from app.adapters.secondary.database.session import Base, SessionLocal, engine

LARGE_RIGGING = "large_rigging"
SPECIAL_LIGHTING = "special_lighting"
PYROTECHNICS = "pyrotechnics"

IRON_VOW = "Iron Vow"
CRIMSON_ENGINE = "Crimson Engine"
THE_LAST_CITADEL = "The Last Citadel"
CONCRETE_REIGN = "Concrete Reign"
ASHES_OF_TOMORROW = "Ashes of Tomorrow"
STATIC_VIOLENCE = "Static Violence"
HOLLOW_MOUNTAIN = "Hollow Mountain"
SOLAR_FUNERAL = "Solar Funeral"
DESERT_CROWN = "Desert Crown"
WINTER_THRONE = "Winter Throne"
NOCTURNAL_VEIL = "Nocturnal Veil"
PALE_KINGDOM = "Pale Kingdom"

MAINSTAGE = "Mainstage"
WARZONE = "Warzone"
VALLEY = "Valley"
TEMPLE = "Temple"

JUNE_18_19H = "2027-06-18T19:00:00"

ARTISTS = (
    (IRON_VOW, "Heavy metal", (LARGE_RIGGING, SPECIAL_LIGHTING)),
    (CRIMSON_ENGINE, "Thrash metal", (SPECIAL_LIGHTING,)),
    (THE_LAST_CITADEL, "Power metal", (LARGE_RIGGING,)),
    (CONCRETE_REIGN, "Hardcore", ()),
    (ASHES_OF_TOMORROW, "Metalcore", (SPECIAL_LIGHTING,)),
    (STATIC_VIOLENCE, "Punk", ()),
    (HOLLOW_MOUNTAIN, "Stoner", (SPECIAL_LIGHTING,)),
    (SOLAR_FUNERAL, "Doom metal", ()),
    (DESERT_CROWN, "Sludge", ()),
    (WINTER_THRONE, "Black metal", (SPECIAL_LIGHTING,)),
    (NOCTURNAL_VEIL, "Black metal", ()),
    (PALE_KINGDOM, "Atmospheric metal", (SPECIAL_LIGHTING,)),
)

STAGES = (
    (MAINSTAGE, 50000, (LARGE_RIGGING, SPECIAL_LIGHTING, PYROTECHNICS)),
    (WARZONE, 15000, (SPECIAL_LIGHTING,)),
    (VALLEY, 8000, (SPECIAL_LIGHTING,)),
    (TEMPLE, 10000, (SPECIAL_LIGHTING,)),
)

# L'ordre fixe les identifiants utilisés dans les scénarios du README.
CONCERTS = (
    (IRON_VOW, MAINSTAGE, "2027-06-18T18:00:00", JUNE_18_19H),
    (CRIMSON_ENGINE, MAINSTAGE, "2027-06-18T19:30:00", "2027-06-18T20:30:00"),
    (THE_LAST_CITADEL, MAINSTAGE, "2027-06-18T21:00:00", "2027-06-18T22:00:00"),
    (CONCRETE_REIGN, WARZONE, "2027-06-18T17:00:00", "2027-06-18T17:45:00"),
    (ASHES_OF_TOMORROW, WARZONE, "2027-06-18T18:15:00", JUNE_18_19H),
    (HOLLOW_MOUNTAIN, VALLEY, JUNE_18_19H, "2027-06-18T20:00:00"),
    (SOLAR_FUNERAL, VALLEY, "2027-06-18T20:30:00", "2027-06-18T21:30:00"),
    (WINTER_THRONE, TEMPLE, "2027-06-18T20:00:00", "2027-06-18T21:00:00"),
    (NOCTURNAL_VEIL, TEMPLE, "2027-06-18T21:30:00", "2027-06-18T22:30:00"),
    (STATIC_VIOLENCE, WARZONE, "2027-06-19T14:00:00", "2027-06-19T14:45:00"),
    (DESERT_CROWN, VALLEY, "2027-06-19T15:00:00", "2027-06-19T16:00:00"),
    (PALE_KINGDOM, TEMPLE, "2027-06-19T16:30:00", "2027-06-19T17:30:00"),
    (IRON_VOW, MAINSTAGE, "2027-06-19T21:00:00", "2027-06-19T22:00:00"),
    (CRIMSON_ENGINE, MAINSTAGE, "2027-06-20T20:00:00", "2027-06-20T21:00:00"),
)


def _clear_tables(db) -> None:
    for model in (Incident, Concert, Stage, Artist, Festival):
        db.query(model).delete()
    db.commit()


def _create_festival(db) -> Festival:
    festival = Festival(
        name="Hellforge Open Air",
        location="Clisson-sur-Rivière",
        start_date=datetime.fromisoformat("2027-06-18T10:00:00"),
        end_date=datetime.fromisoformat("2027-06-20T23:59:00"),
        status="preparation",
    )
    db.add(festival)
    db.commit()
    db.refresh(festival)
    return festival


def _create_artists(db) -> dict[str, Artist]:
    artists = {}
    for name, genre, equipment in ARTISTS:
        artist = Artist(name=name, genre=genre, required_equipment=",".join(equipment))
        db.add(artist)
        db.flush()
        artists[name] = artist
    return artists


def _create_stages(db, festival: Festival) -> dict[str, Stage]:
    stages = {}
    for name, capacity, equipment in STAGES:
        stage = Stage(festival_id=festival.id, name=name, capacity=capacity, available_equipment=",".join(equipment))
        db.add(stage)
        db.flush()
        stages[name] = stage
    db.commit()
    return stages


def _create_concerts(db, festival: Festival, artists: dict[str, Artist], stages: dict[str, Stage]) -> None:
    for artist_name, stage_name, start_time, end_time in CONCERTS:
        db.add(
            Concert(
                festival_id=festival.id,
                artist_id=artists[artist_name].id,
                stage_id=stages[stage_name].id,
                start_time=datetime.fromisoformat(start_time),
                end_time=datetime.fromisoformat(end_time),
                status="scheduled",
            )
        )
    db.commit()


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        _clear_tables(db)
        festival = _create_festival(db)
        artists = _create_artists(db)
        stages = _create_stages(db, festival)
        _create_concerts(db, festival, artists, stages)
        print(
            f"Données chargées : {festival.name}, {len(STAGES)} scènes, "
            f"{len(ARTISTS)} artistes, {len(CONCERTS)} concerts."
        )
    finally:
        db.close()


if __name__ == "__main__":
    seed()
