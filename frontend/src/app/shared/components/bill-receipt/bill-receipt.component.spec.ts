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
    const receipt = billToReceiptData(makeBill({ created_at: '2026-06-03' }), '2026-07-07');

    expect(receipt?.emissionIso).toBe('2026-06-03');
  });

  it('recurre a la fecha de hoy si la factura no tiene created_at (histórica)', () => {
    const receipt = billToReceiptData(makeBill({ created_at: null }), '2026-07-07');

    expect(receipt?.emissionIso).toBe('2026-07-07');
  });

  it('devuelve null para facturas virtuales sin bill_id', () => {
    const receipt = billToReceiptData(makeBill({ bill_id: null }), '2026-07-07');

    expect(receipt).toBeNull();
  });

  it('marca el recibo como pagado con su fecha cuando la factura está Pagada', () => {
    const receipt = billToReceiptData(
      makeBill({ state: 'Pagada', paid_at: '2026-06-05' }),
      '2026-07-07'
    );

    expect(receipt?.paid).toBe(true);
    expect(receipt?.paidAtIso).toBe('2026-06-05');
  });

  it('no marca pagado el recibo de facturas en otros estados', () => {
    const receipt = billToReceiptData(makeBill({ state: 'Creada' }), '2026-07-07');

    expect(receipt?.paid).toBe(false);
    expect(receipt?.paidAtIso).toBeNull();
  });
});
