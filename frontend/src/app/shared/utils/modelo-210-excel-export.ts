import ExcelJS from 'exceljs';

import { Booking } from '../../models/booking.model';

const TEMPLATE_URL = '/templates/modelo_210_alquiler_turistico.xlsx';
const INGRESOS_SHEET = 'Ingresos Modelo 210';

/** Fila de cabecera = 1; datos y estilos de referencia desde la 2. */
const DATA_START_ROW = 2;
/** Columnas A–E (1–5). La F se calcula por fórmula. */
const CONTENT_COLS = [1, 2, 3, 4, 5] as const;
const NETO_COL = 6;

/**
 * Genera el Modelo 210 a partir de la plantilla del cliente.
 * Solo modifica la hoja "Ingresos Modelo 210", columnas A–E (contenido).
 * La columna F queda como fórmula D-E. El resto de hojas y estilos se conservan.
 */
export async function exportModelo210ToExcel(
  bookings: Booking[],
  apartmentId: string
): Promise<void> {
  const workbook = await buildModelo210Workbook(bookings);
  const safeId = apartmentId.trim() || 'piso';
  await downloadWorkbook(workbook, `${safeId} Modelo_210_Alquiler_Turistico.xlsx`);
}

/** Construye el workbook listo para descargar (expuesto para tests). */
export async function buildModelo210Workbook(bookings: Booking[]): Promise<ExcelJS.Workbook> {
  const workbook = await loadTemplate();
  fillIngresosSheet(workbook, bookings);
  return workbook;
}

async function loadTemplate(): Promise<ExcelJS.Workbook> {
  const response = await fetch(TEMPLATE_URL);
  if (!response.ok) {
    throw new Error(`No se pudo cargar la plantilla Modelo 210 (${response.status})`);
  }

  const buffer = await response.arrayBuffer();
  const workbook = new ExcelJS.Workbook();
  await workbook.xlsx.load(buffer);
  return workbook;
}

function fillIngresosSheet(workbook: ExcelJS.Workbook, bookings: Booking[]): void {
  const sheet = workbook.getWorksheet(INGRESOS_SHEET);
  if (!sheet) {
    throw new Error(`Falta la hoja "${INGRESOS_SHEET}" en la plantilla`);
  }

  const styleByCol = captureRowStyles(sheet, DATA_START_ROW);

  // Vaciar A–E (y F) de las filas de datos de ejemplo, conservando el estilo de celda.
  const clearUntil = Math.max(sheet.rowCount, DATA_START_ROW);
  for (let row = DATA_START_ROW; row <= clearUntil; row += 1) {
    for (const col of CONTENT_COLS) {
      clearCellValue(sheet.getCell(row, col));
    }
    clearCellValue(sheet.getCell(row, NETO_COL));
  }

  const sorted = [...bookings].sort((a, b) => a.check_in.localeCompare(b.check_in));

  sorted.forEach((booking, index) => {
    const row = DATA_START_ROW + index;

    writeDateCell(sheet.getCell(row, 1), booking.check_in, styleByCol[1]);
    writeDateCell(sheet.getCell(row, 2), booking.check_out, styleByCol[2]);
    // Columna C (Plataforma): en blanco; se mantiene el estilo.
    applyStyle(sheet.getCell(row, 3), styleByCol[3]);
    writeNumberCell(sheet.getCell(row, 4), booking.price, styleByCol[4]);
    writeNumberCell(sheet.getCell(row, 5), booking.charges, styleByCol[5]);

    const netoCell = sheet.getCell(row, NETO_COL);
    netoCell.value = { formula: `D${row}-E${row}` };
    applyStyle(netoCell, styleByCol[NETO_COL]);
  });
}

function captureRowStyles(
  sheet: ExcelJS.Worksheet,
  row: number
): Record<number, Partial<ExcelJS.Style>> {
  const styles: Record<number, Partial<ExcelJS.Style>> = {};
  for (const col of [...CONTENT_COLS, NETO_COL]) {
    styles[col] = cloneStyle(sheet.getCell(row, col).style);
  }
  return styles;
}

function cloneStyle(style: Partial<ExcelJS.Style>): Partial<ExcelJS.Style> {
  return JSON.parse(JSON.stringify(style ?? {})) as Partial<ExcelJS.Style>;
}

function applyStyle(cell: ExcelJS.Cell, style: Partial<ExcelJS.Style> | undefined): void {
  if (!style || Object.keys(style).length === 0) return;
  cell.style = cloneStyle(style);
}

function clearCellValue(cell: ExcelJS.Cell): void {
  cell.value = null;
}

function writeDateCell(
  cell: ExcelJS.Cell,
  iso: string,
  style: Partial<ExcelJS.Style> | undefined
): void {
  cell.value = isoToUtcDate(iso);
  applyStyle(cell, style);
  if (!cell.numFmt) {
    cell.numFmt = 'DD/MM/YYYY';
  }
}

function writeNumberCell(
  cell: ExcelJS.Cell,
  value: number | null,
  style: Partial<ExcelJS.Style> | undefined
): void {
  applyStyle(cell, style);
  if (value === null || value === undefined || Number.isNaN(value)) {
    cell.value = null;
    return;
  }
  cell.value = value;
}

function isoToUtcDate(iso: string): Date {
  const [year, month, day] = iso.split('-').map(Number);
  return new Date(Date.UTC(year, month - 1, day));
}

async function downloadWorkbook(workbook: ExcelJS.Workbook, filename: string): Promise<void> {
  const buffer = await workbook.xlsx.writeBuffer();
  const blob = new Blob([buffer], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
