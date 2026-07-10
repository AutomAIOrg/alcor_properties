"""
Renderer del PDF de factura mediante Chromium/Chrome headless.

Rellena la plantilla Jinja2 del recibo (bill_templates/bill_receipt.html) con los datos de
la factura, incrusta el logo en base64 y convierte el HTML resultante a PDF invocando el
navegador con `--headless --print-to-pdf`. Se usa Chromium porque el front se renderiza en
un navegador Chromium: así el PDF sale idéntico a la previsualización.

Chromium es una dependencia de SISTEMA (no un paquete pip): debe estar instalado en el
entorno de ejecución. La ruta del binario se fija con BILL_PDF_CHROMIUM_PATH; si se deja
vacía, se autodetecta en el PATH.
"""

import base64
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import cast

from jinja2 import Environment, FileSystemLoader, select_autoescape

from application.bills.bill_pdf_renderer_interface import BillPdfData, IBillPdfRenderer
from domain.exceptions import BillDocumentRenderError
from infrastructure.documents.receipt_context import build_receipt_context

logger = logging.getLogger(__name__)

_TEMPLATE_NAME = "bill_receipt.html"
_LOGO_NAME = "logo_limpieza.PNG"

# backend/infrastructure/documents/ -> backend/bill_templates
_DEFAULT_TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "bill_templates"

# Nombres del binario que se buscan en el PATH (orden de preferencia).
_CHROMIUM_CANDIDATES = (
    "chromium",
    "chromium-browser",
    "google-chrome",
    "google-chrome-stable",
    "chrome",
)

# Rutas típicas en Windows (desarrollo) cuando el binario no está en el PATH.
_WINDOWS_FALLBACKS = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
)

_RENDER_TIMEOUT_SECONDS = 60


class ChromiumBillPdfRenderer(IBillPdfRenderer):
    """Implementación de IBillPdfRenderer con Chromium headless + plantilla Jinja2."""

    def __init__(self, chromium_path: str = "", template_dir: str | Path | None = None) -> None:
        self._chromium_path = chromium_path
        self._template_dir = Path(template_dir) if template_dir else _DEFAULT_TEMPLATE_DIR
        self._env = Environment(
            loader=FileSystemLoader(str(self._template_dir)),
            autoescape=select_autoescape(["html"]),
        )

    def render(self, data: BillPdfData) -> bytes:
        html = self._render_html(data)
        return self._html_to_pdf(html)

    # ------------------------------------------------------------------ #
    # Paso 1: datos -> HTML                                              #
    # ------------------------------------------------------------------ #

    def _render_html(self, data: BillPdfData) -> str:
        try:
            template = self._env.get_template(_TEMPLATE_NAME)
        except Exception as exc:  # jinja2.TemplateNotFound y afines
            raise BillDocumentRenderError(
                f"No se pudo cargar la plantilla '{_TEMPLATE_NAME}' en {self._template_dir}"
            ) from exc

        context = build_receipt_context(data, self._logo_uri())
        return cast(str, template.render(**context))

    def _logo_uri(self) -> str:
        logo_path = self._template_dir / _LOGO_NAME
        try:
            encoded = base64.b64encode(logo_path.read_bytes()).decode("ascii")
        except OSError as exc:
            raise BillDocumentRenderError(f"No se pudo leer el logo en {logo_path}") from exc
        return f"data:image/png;base64,{encoded}"

    # ------------------------------------------------------------------ #
    # Paso 2: HTML -> PDF (Chromium headless)                            #
    # ------------------------------------------------------------------ #

    def _html_to_pdf(self, html: str) -> bytes:
        binary = self._resolve_binary()

        with tempfile.TemporaryDirectory(prefix="bill_pdf_") as tmp:
            tmp_dir = Path(tmp)
            html_path = tmp_dir / "receipt.html"
            pdf_path = tmp_dir / "receipt.pdf"
            html_path.write_text(html, encoding="utf-8")

            command = [
                binary,
                "--headless",
                "--disable-gpu",
                "--no-sandbox",
                "--no-pdf-header-footer",
                f"--user-data-dir={tmp_dir / 'profile'}",
                f"--print-to-pdf={pdf_path}",
                html_path.as_uri(),
            ]

            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    timeout=_RENDER_TIMEOUT_SECONDS,
                    check=False,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                raise BillDocumentRenderError(
                    f"Fallo al invocar Chromium ({binary}) para generar el PDF"
                ) from exc

            if result.returncode != 0 or not pdf_path.exists():
                stderr = result.stderr.decode("utf-8", errors="replace")[:500]
                raise BillDocumentRenderError(
                    f"Chromium terminó con código {result.returncode} sin producir el PDF: {stderr}"
                )

            return pdf_path.read_bytes()

    def _resolve_binary(self) -> str:
        if self._chromium_path:
            return self._chromium_path

        for name in _CHROMIUM_CANDIDATES:
            found = shutil.which(name)
            if found:
                return found

        for path in _WINDOWS_FALLBACKS:
            if os.path.exists(path):
                return path

        raise BillDocumentRenderError(
            "No se encontró un binario de Chromium/Chrome. Instálalo en el entorno o fija su "
            "ruta en la variable de entorno BILL_PDF_CHROMIUM_PATH."
        )
