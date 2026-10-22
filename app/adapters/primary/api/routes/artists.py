from typing import Annotated

from fastapi import APIRouter, Depends

from app.adapters.primary.api.logistics_dependencies import create_artist_use_case, list_artists_use_case
from app.adapters.primary.api.schemas.artist_schemas import ArtistCreateRequest, ArtistResponse
from app.application.use_cases.logistics.create_artist import CreateArtistCommand, CreateArtistUseCase
from app.application.use_cases.logistics.list_artists import ListArtistsUseCase

router = APIRouter(prefix="/artists", tags=["artists"])


@router.get("", response_model=list[ArtistResponse])
def list_artists(use_case: Annotated[ListArtistsUseCase, Depends(list_artists_use_case)]):
    return [ArtistResponse.from_entity(artist) for artist in use_case.execute()]


@router.post("", response_model=ArtistResponse, status_code=201)
def create_artist(
    payload: ArtistCreateRequest,
    use_case: Annotated[CreateArtistUseCase, Depends(create_artist_use_case)],
):
    artist = use_case.execute(
        CreateArtistCommand(name=payload.name, genre=payload.genre, required_equipment=payload.required_equipment)
    )
    return ArtistResponse.from_entity(artist)
