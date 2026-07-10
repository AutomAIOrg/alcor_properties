"""Reintenta sincronizaciones pendientes de documentos de factura con el NAS."""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reintenta documentos de factura pendientes de sincronizar con el NAS."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Número máximo de documentos a procesar en esta ejecución.",
    )
    return parser


def _build_file_storage():
    from config import settings
    from infrastructure.storage.synology_file_storage import SynologyFileStorage

    if not settings.NAS_HOST or not settings.NAS_USER:
        raise RuntimeError(
            "NAS no configurado: defina NAS_HOST, NAS_USER y NAS_PASSWORD en el entorno."
        )

    return SynologyFileStorage(
        host=settings.NAS_HOST,
        port=settings.NAS_PORT,
        username=settings.NAS_USER,
        password=settings.NAS_PASSWORD,
        volume_prefix=settings.NAS_VOLUME_PREFIX,
        connect_timeout=settings.NAS_SSH_TIMEOUT,
    )


def main(argv: list[str] | None = None) -> int:
    from application.bills.retry_bill_document_sync_use_case import RetryBillDocumentSyncUseCase
    from config import settings
    from domain.bills.bill_document import BILL_DOCUMENT_STATUS_COMPLETED
    from infrastructure.database.session import SessionLocal
    from infrastructure.documents.chromium_bill_pdf_renderer import ChromiumBillPdfRenderer
    from infrastructure.repositories.sqlalchemy_apartment_repository import (
        SQLAlchemyApartmentRepository,
    )
    from infrastructure.repositories.sqlalchemy_bill_document_repository import (
        SQLAlchemyBillDocumentRepository,
    )
    from infrastructure.repositories.sqlalchemy_bill_repository import SQLAlchemyBillRepository

    args = _build_parser().parse_args(argv)
    if args.limit <= 0:
        raise RuntimeError("--limit debe ser mayor que cero.")

    with SessionLocal() as session:
        use_case = RetryBillDocumentSyncUseCase(
            bill_repository=SQLAlchemyBillRepository(session),
            document_repository=SQLAlchemyBillDocumentRepository(session),
            apartment_repository=SQLAlchemyApartmentRepository(session),
            pdf_renderer=ChromiumBillPdfRenderer(chromium_path=settings.BILL_PDF_CHROMIUM_PATH),
            file_storage=_build_file_storage(),
            nas_base_path=settings.NAS_BASE_PATH,
        )
        results = use_case.execute(limit=args.limit)

    completed = sum(1 for document in results if document.status == BILL_DOCUMENT_STATUS_COMPLETED)
    failed = len(results) - completed
    print(
        "Sincronización de documentos de factura finalizada: "
        f"{len(results)} procesados, {completed} completados, {failed} pendientes/error."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
