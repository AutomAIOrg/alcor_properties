"""
Enrutador de facturas.
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from api.dependencies import (
    get_create_bill_use_case,
    get_current_user,
    get_generate_and_store_bill_document_use_case,
    get_list_bills_use_case,
    get_list_pending_bills_use_case,
    get_move_paid_bill_document_use_case,
    get_update_bill_state_use_case,
    require_cleaning,
)
from api.v1.bills.schemas import BillCreateRequest, BillResponse, BillUpdateStateRequest
from application.bills.create_bill_use_case import CreateBillData, CreateBillUseCase
from application.bills.generate_and_store_bill_document_use_case import (
    GenerateAndStoreBillDocumentUseCase,
)
from application.bills.list_bills_use_cases import ListBillsUseCase, ListPendingBillsUseCase
from application.bills.move_paid_bill_document_use_case import MovePaidBillDocumentUseCase
from application.bills.update_bill_use_case import UpdateBillStateUseCase
from domain.auth.user_entity import User
from domain.bills.entity import BILL_STATE_PAID, BILL_STATE_PENDING

router = APIRouter(prefix="/bills", tags=["bills"], dependencies=[Depends(get_current_user)])


@router.get("/", response_model=list[BillResponse])
async def list_bills(
    list_bills_use_case: Annotated[ListBillsUseCase, Depends(get_list_bills_use_case)],
    list_pending_bills_use_case: Annotated[
        ListPendingBillsUseCase, Depends(get_list_pending_bills_use_case)
    ],
    apartment_id: str | None = Query(None, description="Filtrar por ID de apartamento"),
    state: str | None = Query(None, description="Filtrar por estado"),
    date_from: date | None = Query(None, description="Fecha de limpieza desde"),
    date_to: date | None = Query(None, description="Fecha de limpieza hasta"),
    cost_min: float | None = Query(None, ge=0, description="Coste mínimo"),
    cost_max: float | None = Query(None, ge=0, description="Coste máximo"),
    _: User = Depends(require_cleaning),
):
    if state == BILL_STATE_PENDING:
        return list_pending_bills_use_case.execute(
            apartment_id=apartment_id,
            date_from=date_from,
            date_to=date_to,
        )

    real_bills = list_bills_use_case.execute(
        apartment_id=apartment_id,
        state=state,
        date_from=date_from,
        date_to=date_to,
        cost_min=cost_min,
        cost_max=cost_max,
    )

    if state is not None:
        return real_bills

    pending = list_pending_bills_use_case.execute(
        apartment_id=apartment_id,
        date_from=date_from,
        date_to=date_to,
    )
    return pending + real_bills


@router.post("/", response_model=BillResponse, status_code=status.HTTP_201_CREATED)
async def create_bill(
    payload: BillCreateRequest,
    create_bill_use_case: Annotated[CreateBillUseCase, Depends(get_create_bill_use_case)],
    document_use_case: Annotated[
        GenerateAndStoreBillDocumentUseCase,
        Depends(get_generate_and_store_bill_document_use_case),
    ],
    current_user: User = Depends(require_cleaning),
):
    data = CreateBillData(**payload.model_dump())
    created_bill = create_bill_use_case.execute(data)
    assert created_bill.bill_id is not None
    document_use_case.execute(created_bill.bill_id, uploaded_by=current_user.id)
    return created_bill


@router.put("/{bill_id}", response_model=BillResponse)
async def update_bill_state(
    bill_id: int,
    payload: BillUpdateStateRequest,
    update_bill_state_use_case: Annotated[
        UpdateBillStateUseCase, Depends(get_update_bill_state_use_case)
    ],
    move_paid_document_use_case: Annotated[
        MovePaidBillDocumentUseCase,
        Depends(get_move_paid_bill_document_use_case),
    ],
    current_user: User = Depends(require_cleaning),
):
    updated_bill = update_bill_state_use_case.execute(
        bill_id,
        payload.state,
        paid_at=payload.paid_at,
        cancellation_note=payload.cancellation_note,
    )
    if updated_bill.state == BILL_STATE_PAID:
        assert updated_bill.bill_id is not None
        move_paid_document_use_case.execute(updated_bill.bill_id, uploaded_by=current_user.id)
    return updated_bill
