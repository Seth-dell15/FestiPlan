from app.adapters.secondary.repositories.in_memory_artist_repository import InMemoryArtistRepository
from app.application.use_cases.logistics.create_artist import CreateArtistCommand, CreateArtistUseCase
from app.application.use_cases.logistics.list_artists import ListArtistsUseCase
from app.domain.value_objects.equipment_set import EquipmentSet


def test_create_artist_turns_equipment_list_into_equipment_set():
    repository = InMemoryArtistRepository()
    command = CreateArtistCommand(name="Iron Vow", genre="Heavy metal", required_equipment=["pyro", " pyro ", ""])

    artist = CreateArtistUseCase(repository).execute(command)

    assert artist.id is not None
    assert artist.required_equipment == EquipmentSet.of(["pyro"])
    assert repository.get(artist.id) is artist


def test_create_artist_without_equipment():
    artist = CreateArtistUseCase(InMemoryArtistRepository()).execute(
        CreateArtistCommand(name="Iron Vow", genre="Heavy metal")
    )

    assert len(artist.required_equipment) == 0


def test_list_artists_sorted_by_name():
    repository = InMemoryArtistRepository()
    create = CreateArtistUseCase(repository)
    create.execute(CreateArtistCommand(name="Zorn", genre="Black metal"))
    create.execute(CreateArtistCommand(name="Abyss", genre="Doom"))

    names = [artist.name for artist in ListArtistsUseCase(repository).execute()]

    assert names == ["Abyss", "Zorn"]
