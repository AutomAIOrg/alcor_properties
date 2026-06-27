import * as XLSX from 'xlsx';

import {
  ApartmentStatsResponse,
  ApartmentStatsYear,
  BookingStatsResponse,
} from '../../models/search.model';

type CellValue = string | number | null;
type Row = CellValue[];
type MetricKind = 'date' | 'integer' | 'decimal' | 'percent' | 'currency';
type MetricRow = {
  metric: string;
  value: CellValue;
  kind?: MetricKind;
};

const CURRENCY_FORMAT = '#,##0.00 €';
const DECIMAL_FORMAT = '#,##0.00';
const INTEGER_FORMAT = '#,##0';
const PERCENT_FORMAT = '0.00%';

function percentValue(value: number | null): number | null {
  return value === null ? null : value / 100;
}

function pendingBookings(statusBreakdown: Record<string, number>): number {
  return Object.entries(statusBreakdown).reduce((total, [status, count]) => {
    const normalizedStatus = status.trim().toLowerCase();
    return normalizedStatus === 'pending' || normalizedStatus === 'pendiente'
      ? total + count
      : total;
  }, 0);
}

function metricRows(
  stats: BookingStatsResponse | ApartmentStatsResponse['filtered_range']
): MetricRow[] {
  return [
    { metric: 'Fecha desde', value: stats.start_date, kind: 'date' },
    { metric: 'Fecha hasta', value: stats.end_date, kind: 'date' },
    { metric: 'Total reservas', value: stats.total_bookings, kind: 'integer' },
    { metric: 'Activas', value: stats.active_bookings, kind: 'integer' },
    { metric: 'Pendientes', value: pendingBookings(stats.status_breakdown), kind: 'integer' },
    { metric: 'Canceladas', value: stats.cancelled_bookings, kind: 'integer' },
    { metric: 'Cancelacion', value: percentValue(stats.cancellation_rate), kind: 'percent' },
    { metric: 'Noches', value: stats.total_nights, kind: 'integer' },
    { metric: 'Media noches/reserva', value: stats.avg_nights_per_booking, kind: 'decimal' },
    { metric: 'Personas', value: stats.total_persons, kind: 'integer' },
    { metric: 'Media personas/reserva', value: stats.avg_persons_per_booking, kind: 'decimal' },
    { metric: 'Ocupacion', value: percentValue(stats.occupancy_pct), kind: 'percent' },
    { metric: 'Ingresos', value: stats.total_revenue, kind: 'currency' },
    { metric: 'Media ingreso/reserva', value: stats.avg_revenue_per_booking, kind: 'currency' },
    { metric: 'Media ingreso/noche', value: stats.avg_revenue_per_night, kind: 'currency' },
    { metric: 'Cargos', value: stats.total_charges, kind: 'currency' },
    { metric: 'Electricidad', value: stats.total_electric_allowance, kind: 'currency' },
  ];
}

function rowsFromMetrics(rows: MetricRow[]): Row[] {
  return rows.map(row => [row.metric, row.value]);
}

function yearRows(years: ApartmentStatsYear[]): Row[] {
  return years.map(year => [
    year.year,
    year.total_bookings,
    year.active_bookings,
    year.cancelled_bookings,
    percentValue(year.cancellation_rate),
    year.total_nights,
    year.total_days_in_year,
    percentValue(year.occupancy_pct),
    year.total_revenue,
    year.avg_revenue_per_booking,
    year.total_charges,
    year.total_electric_allowance,
  ]);
}

function setCellFormat(worksheet: XLSX.WorkSheet, address: string, kind?: MetricKind): void {
  const cell = worksheet[address];
  if (!cell || cell.v === null || cell.v === undefined || !kind || kind === 'date') return;

  if (kind === 'integer') cell.z = INTEGER_FORMAT;
  if (kind === 'decimal') cell.z = DECIMAL_FORMAT;
  if (kind === 'percent') cell.z = PERCENT_FORMAT;
  if (kind === 'currency') cell.z = CURRENCY_FORMAT;
}

function formatMetricSheet(
  worksheet: XLSX.WorkSheet,
  metricStartRow: number,
  metrics: MetricRow[]
): void {
  worksheet['!cols'] = [{ wch: 28 }, { wch: 18 }];
  worksheet['!freeze'] = { xSplit: 0, ySplit: metricStartRow };
  worksheet['!autofilter'] = {
    ref: `A${metricStartRow}:B${metricStartRow + metrics.length}`,
  };

  metrics.forEach((metric, index) => {
    setCellFormat(worksheet, `B${metricStartRow + index + 1}`, metric.kind);
  });
}

function formatYearSheet(worksheet: XLSX.WorkSheet, rowCount: number): void {
  worksheet['!cols'] = [
    { wch: 10 },
    { wch: 12 },
    { wch: 12 },
    { wch: 12 },
    { wch: 14 },
    { wch: 12 },
    { wch: 12 },
    { wch: 14 },
    { wch: 14 },
    { wch: 16 },
    { wch: 14 },
    { wch: 14 },
  ];
  worksheet['!freeze'] = { xSplit: 0, ySplit: 1 };
  worksheet['!autofilter'] = { ref: `A1:L${rowCount}` };

  for (let row = 2; row <= rowCount; row += 1) {
    ['A', 'B', 'C', 'D', 'F', 'G'].forEach(column =>
      setCellFormat(worksheet, `${column}${row}`, 'integer')
    );
    ['E', 'H'].forEach(column => setCellFormat(worksheet, `${column}${row}`, 'percent'));
    ['I', 'J', 'K', 'L'].forEach(column => setCellFormat(worksheet, `${column}${row}`, 'currency'));
  }
}

function appendMetricSheet(
  workbook: XLSX.WorkBook,
  sheetName: string,
  title: string,
  metrics: MetricRow[],
  contextRows: Row[] = []
): void {
  const metricStartRow = contextRows.length + 3;
  const rows: Row[] = [
    [title],
    ...contextRows,
    [],
    ['Metrica', 'Valor'],
    ...rowsFromMetrics(metrics),
  ];
  const worksheet = XLSX.utils.aoa_to_sheet(rows);
  formatMetricSheet(worksheet, metricStartRow, metrics);
  XLSX.utils.book_append_sheet(workbook, worksheet, sheetName);
}

export function exportBookingStatsToExcel(stats: BookingStatsResponse): void {
  const workbook = XLSX.utils.book_new();
  appendMetricSheet(workbook, 'Estadisticas', 'Estadisticas de reservas', metricRows(stats));
  XLSX.writeFile(workbook, 'estadisticas-reservas.xlsx');
}

export function exportApartmentStatsToExcel(stats: ApartmentStatsResponse): void {
  const workbook = XLSX.utils.book_new();
  appendMetricSheet(
    workbook,
    'Estadisticas',
    `Estadisticas del piso ${stats.apartment_id}`,
    metricRows(stats.filtered_range),
    [
      ['Piso', stats.apartment_id],
      ['Comunidad', stats.apartment.community],
      ['Direccion', stats.apartment.address],
    ]
  );

  if (stats.by_year.length > 0) {
    const rows: Row[] = [
      [
        'Ano',
        'Reservas',
        'Activas',
        'Canceladas',
        'Cancelacion',
        'Noches',
        'Dias ano',
        'Ocupacion',
        'Ingresos',
        'Media/reserva',
        'Cargos',
        'Electricidad',
      ],
      ...yearRows(stats.by_year),
    ];
    const worksheet = XLSX.utils.aoa_to_sheet(rows);
    formatYearSheet(worksheet, rows.length);
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Ocupacion por ano');
  }

  XLSX.writeFile(workbook, `estadisticas-piso-${stats.apartment_id}.xlsx`);
}
