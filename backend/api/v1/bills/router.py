"""
Enrutador de facturas.
"""

import logging
import unicodedata
from datetime import date
from decimal import Decimal
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Response, status

from api.dependencies import (
    get_create_bill_use_case,
    get_current_user,
    get_generate_and_store_bill_document_use_case,
    get_list_bills_use_case,
    get_list_pending_bills_use_case,
    get_move_paid_bill_document_use_case,
    get_rectify_bill_use_case,
    get_render_bill_document_use_case,
    get_update_bill_state_use_case,
    require_cleaning,
)
from api.v1.bills.schemas import (
    BillCreateRequest,
    BillRectifyRequest,
    BillResponse,
    BillUpdateStateRequest,
)
from application.bills.bill_document_helpers import CONTENT_TYPE_PDF
from application.bills.create_bill_use_case import CreateBillData, CreateBillUseCase
from application.bills.generate_and_store_bill_document_use_case import (
    GenerateAndStoreBillDocumentUseCase,
)
from application.bills.list_bills_use_cases import ListBillsUseCase, ListPendingBillsUseCase
from application.bills.move_paid_bill_document_use_case import MovePaidBillDocumentUseCase
from application.bills.render_bill_document_use_case import RenderBillDocumentUseCase
from application.bills.update_bill_use_case import RectifyBillUseCase, UpdateBillStateUseCase
from domain.auth.user_entity import User
from domain.bills.entity import BILL_STATE_PAID, BILL_STATE_PENDING

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


def _content_disposition(filename: str) -> str:
    """
    Cabecera de descarga para el recibo.

    El nombre del archivo lleva espacios y puntos ("A101 LIMPIEZA 03.07.2026.pdf"), así que
    debe ir entrecomillado o el navegador lo trunca en el primer espacio. Se acompaña de
    filename* (RFC 5987) por si el ID del apartamento trae algún carácter no ASCII, que no
    cabe en la forma entrecomillada.
    """
    ascii_name = (
        unicodedata.normalize("NFKD", filename).encode("ascii", "ignore").decode().replace('"', "")
    )
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename)}"


@router.get(
    "/{bill_id}/document",
    response_class=Response,
    responses={200: {"content": {CONTENT_TYPE_PDF: {}}, "description": "Recibo de la factura"}},
)
def download_bill_document(
    bill_id: int,
    render_use_case: Annotated[
        RenderBillDocumentUseCase, Depends(get_render_bill_document_use_case)
    ],
    _: User = Depends(require_cleaning),
):
    """
    Descarga el recibo de una factura, generado al vuelo y servido directamente.

    No pasa por el NAS: el PDF archivado allí es el registro contable, este es una copia
    para el usuario. Se declara síncrono (no `async`) a propósito: el render invoca a
    Chromium y tarda un segundo o dos, así que FastAPI lo ejecuta en un hilo aparte en lugar
    de bloquear el bucle de eventos.
    """
    document = render_use_case.execute(bill_id)
    return Response(
        content=document.content,
        media_type=CONTENT_TYPE_PDF,
        headers={"Content-Disposition": _content_disposition(document.filename)},
    )


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
    # Al quedar la factura "Creada" se genera su recibo PDF (Chromium) y se sube al NAS.
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
        actor=current_user,
        paid_at=payload.paid_at,
        cancellation_note=payload.cancellation_note,
    )
    # Al completarse el pago, el recibo se regenera (versión "pagada") y se mueve a la carpeta
    # de facturas pagadas del NAS.
    if updated_bill.state == BILL_STATE_PAID:
        assert updated_bill.bill_id is not None
        move_paid_document_use_case.execute(updated_bill.bill_id, uploaded_by=current_user.id)
    return updated_bill


@router.put("/{bill_id}/rectify", response_model=BillResponse)
async def rectify_bill(
    bill_id: int,
    payload: BillRectifyRequest,
    rectify_bill_use_case: Annotated[RectifyBillUseCase, Depends(get_rectify_bill_use_case)],
    document_use_case: Annotated[
        GenerateAndStoreBillDocumentUseCase,
        Depends(get_generate_and_store_bill_document_use_case),
    ],
    current_user: User = Depends(require_cleaning),
):
    bill = rectify_bill_use_case.execute(
        bill_id,
        cleaning_date=payload.cleaning_date,
        # El DTO trae las horas como float (JSON); el dominio trabaja con Decimal. str()
        # evita el ruido binario del float (Decimal(str(2.5)) == Decimal("2.5")).
        clean_hours=Decimal(str(payload.clean_hours)),
        cleaning_type_id=payload.cleaning_type_id,
    )

    # La factura corregida sigue "Creada": se regenera EN EL SITIO su recibo PDF en el NAS con
    # los nuevos importes (el mismo documento, sin crear un segundo PDF). Un fallo aquí no debe
    # impedir la rectificación.
    assert bill.bill_id is not None
    try:
        document_use_case.execute(bill.bill_id, uploaded_by=current_user.id, regenerate=True)
    except Exception:
        logger.exception("No se pudo regenerar el PDF de la factura rectificada %s", bill.bill_id)

    return bill
