import * as XLSX from 'xlsx';

import { ApartmentStatsResponse, BookingStatsResponse } from '../../models/search.model';
import { exportApartmentStatsToExcel, exportBookingStatsToExcel } from './stats-excel-export';

jest.mock('xlsx', () => {
  const writeFile = jest.fn();
  return {
    utils: {
      book_new: jest.fn(() => ({ SheetNames: [], Sheets: {} })),
      aoa_to_sheet: jest.fn(rows => ({ rows })),
      book_append_sheet: jest.fn((workbook, worksheet, sheetName) => {
        workbook.SheetNames.push(sheetName);
        workbook.Sheets[sheetName] = worksheet;
      }),
    },
    writeFile,
  };
});

function makeBookingStats(): BookingStatsResponse {
  return {
    total_bookings: 2,
    active_bookings: 1,
    cancelled_bookings: 0,
    cancellation_rate: 0,
    total_nights: 4,
    avg_nights_per_booking: 4,
    total_persons: 2,
    avg_persons_per_booking: 2,
    total_revenue: 500,
    avg_revenue_per_booking: 500,
    avg_revenue_per_night: 125,
    total_charges: null,
    total_electric_allowance: 20,
    status_breakdown: { Confirmed: 1, Pending: 1 },
    start_date: '2026-01-01',
    end_date: '2026-12-31',
    occupancy_pct: null,
    no_booking_days_pct: null,
  };
}

function makeApartmentStats(): ApartmentStatsResponse {
  return {
    apartment_id: 'R101',
    apartment: {
      apartment_id: 'R101',
      community: 'Centro',
      apartment_description: null,
      address: 'Calle Mayor 1',
      rooms: 2,
      bathrooms: 1,
      parking: 'yes',
      total_occupants: 4,
      owner_name: 'Ana',
      email: null,
      phone: null,
    },
    filtered_range: makeBookingStats(),
    by_year: [
      {
        year: 2026,
        total_bookings: 2,
        active_bookings: 1,
        cancelled_bookings: 0,
        cancellation_rate: 0,
        total_nights: 4,
        avg_nights_per_booking: 4,
        total_days_in_year: 365,
        occupancy_pct: 10,
        total_revenue: 500,
        avg_revenue_per_booking: 500,
        total_charges: null,
        total_electric_allowance: 20,
      },
    ],
  };
}

describe('stats excel export', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('genera un archivo xlsx con las estadisticas de reservas', () => {
    exportBookingStatsToExcel(makeBookingStats());

    const writeFileMock = XLSX.writeFile as jest.Mock;
    const workbook = writeFileMock.mock.calls[0][0] as XLSX.WorkBook;
    const worksheet = workbook.Sheets['Estadisticas'];

    expect(XLSX.writeFile).toHaveBeenCalledWith(workbook, 'estadisticas-reservas.xlsx');
    expect(workbook.SheetNames).toEqual(['Estadisticas']);
    expect(worksheet['!cols']).toEqual([{ wch: 28 }, { wch: 18 }]);
    expect(worksheet['!autofilter']).toEqual({ ref: 'A3:B20' });
  });

  it('genera un archivo xlsx de piso con hojas de estadisticas y ocupacion anual', () => {
    exportApartmentStatsToExcel(makeApartmentStats());

    const writeFileMock = XLSX.writeFile as jest.Mock;
    const workbook = writeFileMock.mock.calls[0][0] as XLSX.WorkBook;
    const yearSheet = workbook.Sheets['Ocupacion por ano'];

    expect(XLSX.writeFile).toHaveBeenCalledWith(workbook, 'estadisticas-piso-R101.xlsx');
    expect(workbook.SheetNames).toEqual(['Estadisticas', 'Ocupacion por ano']);
    expect(yearSheet['!freeze']).toEqual({ xSplit: 0, ySplit: 1 });
    expect(yearSheet['!autofilter']).toEqual({ ref: 'A1:L2' });
  });
});
