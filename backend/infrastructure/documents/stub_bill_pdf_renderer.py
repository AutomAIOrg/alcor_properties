"""
Renderer stub de PDF de factura.

Devuelve un PDF mínimo válido hasta que se implemente la plantilla real.
"""

from application.bills.bill_pdf_renderer_interface import BillPdfData, IBillPdfRenderer

_MINIMAL_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n"
    b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n"
    b"0000000052 00000 n \n0000000101 00000 n \n"
    b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF\n"
)


class StubBillPdfRenderer(IBillPdfRenderer):
    """Implementación temporal que genera un PDF mínimo con metadatos embebidos en comentarios."""

    def render(self, data: BillPdfData) -> bytes:
        metadata = (
            f"bill_id={data.bill_id};"
            f"apartment={data.apartment_id};"
            f"date={data.cleaning_date.isoformat()};"
            f"hours={data.clean_hours};"
            f"rate={data.hourly_rate};"
            f"total={data.total_cost}"
        )
        return _MINIMAL_PDF + f"% Stub metadata: {metadata}\n".encode()
