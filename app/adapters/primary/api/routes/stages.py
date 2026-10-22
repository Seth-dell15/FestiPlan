from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.adapters.primary.api.logistics_dependencies import create_stage_use_case, list_stages_use_case
from app.adapters.primary.api.schemas.stage_schemas import StageCreateRequest, StageResponse
from app.application.use_cases.logistics.create_stage import CreateStageCommand, CreateStageUseCase
from app.application.use_cases.logistics.list_stages import ListStagesUseCase
from app.domain.exceptions.logistics_exceptions import LogisticsError

router = APIRouter(prefix="/stages", tags=["stages"])


@router.get("", response_model=list[StageResponse])
def list_stages(festival_id: int, use_case: Annotated[ListStagesUseCase, Depends(list_stages_use_case)]):
    return [StageResponse.from_entity(stage) for stage in use_case.execute(festival_id)]


@router.post(
    "",
    response_model=StageResponse,
    status_code=201,
    responses={400: {"description": "Festival introuvable ou règle métier non respectée"}},
)
def create_stage(
    payload: StageCreateRequest,
    use_case: Annotated[CreateStageUseCase, Depends(create_stage_use_case)],
):
    command = CreateStageCommand(
        festival_id=payload.festival_id,
        name=payload.name,
        capacity=payload.capacity,
        available_equipment=payload.available_equipment,
    )
    try:
        stage = use_case.execute(command)
    except LogisticsError as exc:
        # 400 comme l'ancienne route, y compris pour un festival inconnu.
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return StageResponse.from_entity(stage)
