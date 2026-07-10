import { Bill } from '../../../models/bill.model';
import { billToReceiptData } from './bill-receipt.component';

function makeBill(overrides: Partial<Bill> = {}): Bill {
  return {
    bill_id: 1,
    record_id: 5,
    apartment_id: 'R180',
    cleaning_date: '2026-06-02',
    clean_hours: 2,
    cost: 30,
    hourly_rate: 15,
    cleaning_type_id: 1,
    cleaning_type_name: 'Limpieza normal',
    state: 'Creada',
    paid_at: null,
    paid_confirmed_by_admin: null,
    paid_confirmed_by_admin_name: null,
    paid_confirmed_by_cleaner: null,
    paid_confirmed_by_cleaner_name: null,
    cancellation_note: null,
    previously_cancelled: false,
    address: null,
    apartment_description: null,
    created_at: null,
    ...overrides,
  };
}

describe('billToReceiptData', () => {
  it('usa el created_at congelado de la factura como fecha de emisión', () => {
    const receipt = billToReceiptData(makeBill({ created_at: '2026-06-03' }));

    expect(receipt?.emissionIso).toBe('2026-06-03');
  });

  it('recurre a la fecha de limpieza (estable) si la factura no tiene created_at (histórica)', () => {
    const receipt = billToReceiptData(makeBill({ created_at: null, cleaning_date: '2026-06-02' }));

    expect(receipt?.emissionIso).toBe('2026-06-02');
  });

  it('devuelve null para facturas virtuales sin bill_id', () => {
    const receipt = billToReceiptData(makeBill({ bill_id: null }));

    expect(receipt).toBeNull();
  });

  it('marca el recibo como pagado con su fecha cuando la factura está Pagada', () => {
    const receipt = billToReceiptData(makeBill({ state: 'Pagada', paid_at: '2026-06-05' }));

    expect(receipt?.paid).toBe(true);
    expect(receipt?.paidAtIso).toBe('2026-06-05');
  });

  it('no marca pagado el recibo de facturas en otros estados', () => {
    const receipt = billToReceiptData(makeBill({ state: 'Creada' }));

    expect(receipt?.paid).toBe(false);
    expect(receipt?.paidAtIso).toBeNull();
  });

  it('incluye la confirmación de pago de la parte que ya haya confirmado', () => {
    const receipt = billToReceiptData(
      makeBill({
        state: 'Creada',
        paid_confirmed_by_admin: '2026-06-03T14:30:00',
        paid_confirmed_by_admin_name: 'Admin User',
      })
    );

    expect(receipt?.paidConfirmations).toEqual([
      { name: 'Admin User', datetimeIso: '2026-06-03T14:30:00' },
    ]);
  });

  it('incluye ambas confirmaciones, en orden, cuando ambas partes han confirmado', () => {
    const receipt = billToReceiptData(
      makeBill({
        state: 'Pagada',
        paid_at: '2026-06-04',
        paid_confirmed_by_admin: '2026-06-03T14:30:00',
        paid_confirmed_by_admin_name: 'Admin User',
        paid_confirmed_by_cleaner: '2026-06-04T09:15:00',
        paid_confirmed_by_cleaner_name: 'Limpiadora Test',
      })
    );

    expect(receipt?.paidConfirmations).toEqual([
      { name: 'Admin User', datetimeIso: '2026-06-03T14:30:00' },
      { name: 'Limpiadora Test', datetimeIso: '2026-06-04T09:15:00' },
    ]);
  });

  it('no incluye confirmaciones cuando ninguna parte ha confirmado', () => {
    const receipt = billToReceiptData(makeBill());

    expect(receipt?.paidConfirmations).toEqual([]);
  });
});
