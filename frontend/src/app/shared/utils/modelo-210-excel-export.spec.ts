import ExcelJS from 'exceljs';

import { Booking } from '../../models/booking.model';
import { buildModelo210Workbook, exportModelo210ToExcel } from './modelo-210-excel-export';

function makeBooking(overrides: Partial<Booking> = {}): Booking {
  return {
    record_id: 1,
    apartment_id: 'R223',
    guest_name: 'Ana',
    check_in: '2025-07-07',
    check_out: '2025-07-13',
    check_in_time: null,
    check_out_time: null,
    status: 'Confirmed',
    nights: 6,
    persons: 2,
    adults: 2,
    children: 0,
    price: 1096.5,
    charges: 216.26,
    electric_allowance: 40,
    email: null,
    phone: null,
    booking_number: 'BK-1',
    notes: null,
    notes_cleaning: null,
    ...overrides,
  };
}

async function buildTemplateBuffer(): Promise<ArrayBuffer> {
  const workbook = new ExcelJS.Workbook();

  const ingresos = workbook.addWorksheet('Ingresos Modelo 210');
  ingresos.getCell('A1').value = 'Fecha Entrada';
  ingresos.getCell('B1').value = 'Fecha Salida';
  ingresos.getCell('C1').value = 'Plataforma';
  ingresos.getCell('D1').value = 'Importe Bruto (€)';
  ingresos.getCell('E1').value = 'Comisión Plataforma (€)';
  ingresos.getCell('F1').value = 'Ingreso Neto (€)';
  ingresos.getCell('H2').value = { formula: 'SUM(D2:D301)' };
  ingresos.getCell('I2').value = { formula: 'SUM(E2:E301)' };
  ingresos.getCell('J2').value = { formula: 'SUM(F2:F301)' };

  ingresos.getCell('A2').value = new Date(Date.UTC(2025, 6, 7));
  ingresos.getCell('A2').numFmt = 'DD/MM/YYYY';
  ingresos.getCell('A2').font = { name: 'Calibri', size: 11 };
  ingresos.getCell('B2').value = new Date(Date.UTC(2025, 6, 13));
  ingresos.getCell('B2').numFmt = 'DD/MM/YYYY';
  ingresos.getCell('C2').value = 'Booking.com';
  ingresos.getCell('D2').value = 100;
  ingresos.getCell('D2').numFmt = '#,##0.00 €';
  ingresos.getCell('E2').value = 20;
  ingresos.getCell('E2').numFmt = '#,##0.00 €';
  ingresos.getCell('F2').value = 80;
  ingresos.getCell('F2').numFmt = '#,##0.00 €';

  const gastos = workbook.addWorksheet('Gastos Deducibles');
  gastos.getCell('A1').value = 'Fecha';
  gastos.getCell('A2').value = 'sample-gasto';
  gastos.getCell('G2').value = { formula: 'SUM(E2:E38)' };

  workbook.addWorksheet('Resumen Modelo 210');

  return (await workbook.xlsx.writeBuffer()) as ArrayBuffer;
}

describe('modelo-210-excel-export', () => {
  const fetchMock = jest.fn();
  const originalCreateElement = document.createElement.bind(document);
  let templateBuffer: ArrayBuffer;
  let createdAnchors: HTMLAnchorElement[] = [];

  beforeAll(async () => {
    templateBuffer = await buildTemplateBuffer();
  });

  beforeEach(() => {
    createdAnchors = [];
    (globalThis as unknown as { fetch: typeof fetch }).fetch = fetchMock as unknown as typeof fetch;
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      arrayBuffer: async () => templateBuffer.slice(0),
    });
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('buildModelo210Workbook', () => {
    it('escribe A–E, deja F como fórmula, no incluye luz y no toca Gastos', async () => {
      const workbook = await buildModelo210Workbook([
        makeBooking({
          check_in: '2025-08-01',
          check_out: '2025-08-05',
          price: 200,
          charges: 30,
        }),
        makeBooking({
          check_in: '2025-07-07',
          check_out: '2025-07-13',
          price: 1096.5,
          charges: 216.26,
          electric_allowance: 999,
        }),
      ]);

      const ingresos = workbook.getWorksheet('Ingresos Modelo 210')!;
      expect(ingresos.getCell('D2').value).toBe(1096.5);
      expect(ingresos.getCell('E2').value).toBe(216.26);
      expect(ingresos.getCell('C2').value).toBeNull();
      expect(ingresos.getCell('D2').value).not.toBe(999);
      expect(ingresos.getCell('F2').value).toEqual(expect.objectContaining({ formula: 'D2-E2' }));
      expect(ingresos.getCell('D3').value).toBe(200);
      expect(ingresos.getCell('F3').value).toEqual(expect.objectContaining({ formula: 'D3-E3' }));
      expect(ingresos.getCell('H2').value).toEqual(
        expect.objectContaining({ formula: 'SUM(D2:D301)' })
      );
      expect(ingresos.getCell('D2').numFmt).toContain('#,##0.00');

      const gastos = workbook.getWorksheet('Gastos Deducibles')!;
      expect(gastos.getCell('A2').value).toBe('sample-gasto');
    });
  });

  describe('exportModelo210ToExcel', () => {
    beforeEach(() => {
      Object.defineProperty(URL, 'createObjectURL', {
        configurable: true,
        writable: true,
        value: jest.fn().mockReturnValue('blob:mock'),
      });
      Object.defineProperty(URL, 'revokeObjectURL', {
        configurable: true,
        writable: true,
        value: jest.fn(),
      });
      jest.spyOn(document, 'createElement').mockImplementation((tag: string) => {
        if (tag === 'a') {
          const anchor = {
            href: '',
            download: '',
            click: jest.fn(),
          } as unknown as HTMLAnchorElement;
          createdAnchors.push(anchor);
          return anchor;
        }
        return originalCreateElement(tag);
      });
    });

    it('descarga el archivo con el apartment_id en el nombre', async () => {
      await exportModelo210ToExcel([makeBooking()], 'R223');

      expect(fetchMock).toHaveBeenCalledWith('/templates/modelo_210_alquiler_turistico.xlsx');
      expect(createdAnchors[0]?.download).toBe('R223 Modelo_210_Alquiler_Turistico.xlsx');
      expect(createdAnchors[0]?.click).toHaveBeenCalled();
    });
  });
});
