"""
Enrutador de facturas.
"""

import logging
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from api.dependencies import (
    get_create_bill_use_case,
    get_current_user,
    get_generate_bill_document_use_case,
    get_list_bills_use_case,
    get_list_pending_bills_use_case,
    get_update_bill_state_use_case,
    require_cleaning,
)
from api.v1.bills.schemas import BillCreateRequest, BillResponse, BillUpdateStateRequest
from application.bills.create_bill_use_case import CreateBillData, CreateBillUseCase
from application.bills.generate_bill_document_use_case import GenerateBillDocumentUseCase
from application.bills.list_bills_use_cases import ListBillsUseCase, ListPendingBillsUseCase
from application.bills.update_bill_use_case import UpdateBillStateUseCase
from domain.auth.user_entity import User
from domain.bills.entity import BILL_STATE_PENDING

logger = logging.getLogger(__name__)

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
    generate_bill_document_use_case: Annotated[
        GenerateBillDocumentUseCase, Depends(get_generate_bill_document_use_case)
    ],
    _: User = Depends(require_cleaning),
):
    data = CreateBillData(**payload.model_dump())
    bill = create_bill_use_case.execute(data)

    # Al quedar la factura "Creada" se genera su recibo PDF. Un fallo aquí no debe impedir
    # la creación de la factura: se registra y se devuelve la factura igualmente.
    try:
        generate_bill_document_use_case.execute(bill)
    except Exception:
        logger.exception("No se pudo generar el PDF de la factura %s", bill.bill_id)

    return bill


@router.put("/{bill_id}", response_model=BillResponse)
async def update_bill_state(
    bill_id: int,
    payload: BillUpdateStateRequest,
    update_bill_state_use_case: Annotated[
        UpdateBillStateUseCase, Depends(get_update_bill_state_use_case)
    ],
    _: User = Depends(require_cleaning),
):
    return update_bill_state_use_case.execute(
        bill_id,
        payload.state,
        paid_at=payload.paid_at,
        cancellation_note=payload.cancellation_note,
    )
