"""
Enrutador de facturas.
"""

from datetime import date

from fastapi import APIRouter, Depends, Query, status

from api.dependencies import (
    BillUseCases,
    get_bill_use_cases,
    get_current_user,
    require_cleaning,
)
from api.v1.bills.schemas import BillCreateRequest, BillResponse, BillUpdateStateRequest
from application.bills.commands import CreateBillData
from domain.auth.user_entity import User

router = APIRouter(prefix="/bills", tags=["bills"], dependencies=[Depends(get_current_user)])


@router.get("/", response_model=list[BillResponse])
async def list_bills(
    apartment_id: str | None = Query(None, description="Filtrar por ID de apartamento"),
    state: str | None = Query(None, description="Filtrar por estado"),
    date_from: date | None = Query(None, description="Fecha de limpieza desde"),
    date_to: date | None = Query(None, description="Fecha de limpieza hasta"),
    cost_min: float | None = Query(None, ge=0, description="Coste mínimo"),
    cost_max: float | None = Query(None, ge=0, description="Coste máximo"),
    use_cases: BillUseCases = Depends(get_bill_use_cases),
    _: User = Depends(require_cleaning),
):
    if state == "Pendiente":
        return use_cases.list_pending_query.execute(
            apartment_id=apartment_id,
            date_from=date_from,
            date_to=date_to,
        )

    real_bills = use_cases.list_query.execute(
        apartment_id=apartment_id,
        state=state,
        date_from=date_from,
        date_to=date_to,
        cost_min=cost_min,
        cost_max=cost_max,
    )

    if state is not None:
        return real_bills

    pending = use_cases.list_pending_query.execute(
        apartment_id=apartment_id,
        date_from=date_from,
        date_to=date_to,
    )
    return pending + real_bills


@router.post("/", response_model=BillResponse, status_code=status.HTTP_201_CREATED)
async def create_bill(
    payload: BillCreateRequest,
    use_cases: BillUseCases = Depends(get_bill_use_cases),
    _: User = Depends(require_cleaning),
):
    data = CreateBillData(**payload.model_dump())
    return use_cases.create_command.execute(data)


@router.patch("/{bill_id}", response_model=BillResponse)
async def update_bill_state(
    bill_id: int,
    payload: BillUpdateStateRequest,
    use_cases: BillUseCases = Depends(get_bill_use_cases),
    _: User = Depends(require_cleaning),
):
    return use_cases.update_state_command.execute(bill_id, payload.state, paid_at=payload.paid_at)
