import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';

import { environment } from '../../environments/environment';
import { Bill, BillCreateRequest } from '../models/bill.model';
import { BillService } from './bill.service';

function makeBill(overrides: Partial<Bill> = {}): Bill {
  return {
    bill_id: 1,
    record_id: 5,
    apartment_id: 'R180',
    cleaning_date: '2026-06-02',
    clean_hours: 2,
    cost: 30,
    hourly_rate: 15,
    state: 'Creada',
    paid_at: null,
    cancellation_note: null,
    previously_cancelled: false,
    ...overrides,
  };
}

describe('BillService', () => {
  let service: BillService;
  let httpMock: HttpTestingController;

  const API = `${environment.apiUrl}/api/v1`;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [BillService, provideHttpClient(), provideHttpClientTesting()],
    });

    service = TestBed.inject(BillService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  describe('getCleaningRate', () => {
    it('hace GET al endpoint de tarifa y devuelve la respuesta', () => {
      let result: { cleaning_hourly_rate: number } | undefined;

      service.getCleaningRate().subscribe(response => {
        result = response;
      });

      const req = httpMock.expectOne(`${API}/settings/cleaning-rate`);
      expect(req.request.method).toBe('GET');
      req.flush({ cleaning_hourly_rate: 18 });

      expect(result).toEqual({ cleaning_hourly_rate: 18 });
    });
  });

  describe('createBill', () => {
    it('hace POST al endpoint de facturas y devuelve la factura creada', () => {
      const payload: BillCreateRequest = {
        record_id: 5,
        cleaning_date: '2026-06-02',
        start_time: '10:00',
        end_time: '12:00',
      };
      const created = makeBill();
      let result: Bill | undefined;

      service.createBill(payload).subscribe(response => {
        result = response;
      });

      const req = httpMock.expectOne(`${API}/bills/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(payload);
      req.flush(created);

      expect(result).toEqual(created);
    });
  });

  describe('listBills', () => {
    it('hace GET con filtros como query params', () => {
      const bills = [makeBill(), makeBill({ bill_id: 2, apartment_id: 'R101' })];
      let result: Bill[] | undefined;

      service
        .listBills({
          apartment_id: 'R180',
          state: 'Creada',
          date_from: '2026-06-01',
          date_to: '2026-06-30',
          cost_min: 10,
          cost_max: 50,
        })
        .subscribe(response => {
          result = response;
        });

      const req = httpMock.expectOne(
        request =>
          request.url === `${API}/bills/` &&
          request.params.get('apartment_id') === 'R180' &&
          request.params.get('state') === 'Creada' &&
          request.params.get('date_from') === '2026-06-01' &&
          request.params.get('date_to') === '2026-06-30' &&
          request.params.get('cost_min') === '10' &&
          request.params.get('cost_max') === '50'
      );
      expect(req.request.method).toBe('GET');
      req.flush(bills);

      expect(result).toEqual(bills);
    });
  });

  describe('updateBillState', () => {
    it('hace PUT al endpoint de factura con el nuevo estado', () => {
      const updated = makeBill({ state: 'Pagada', paid_at: '2026-06-03' });
      let result: Bill | undefined;

      service.updateBillState(1, { state: 'Pagada', paid_at: '2026-06-03' }).subscribe(response => {
        result = response;
      });

      const req = httpMock.expectOne(`${API}/bills/1`);
      expect(req.request.method).toBe('PUT');
      expect(req.request.body).toEqual({ state: 'Pagada', paid_at: '2026-06-03' });
      req.flush(updated);

      expect(result).toEqual(updated);
    });
  });

  describe('updateCleaningRate', () => {
    it('hace PUT al endpoint de tarifa', () => {
      let result: { cleaning_hourly_rate: number } | undefined;

      service.updateCleaningRate(20).subscribe(response => {
        result = response;
      });

      const req = httpMock.expectOne(`${API}/settings/cleaning-rate`);
      expect(req.request.method).toBe('PUT');
      expect(req.request.body).toEqual({ cleaning_hourly_rate: 20 });
      req.flush({ cleaning_hourly_rate: 20 });

      expect(result).toEqual({ cleaning_hourly_rate: 20 });
    });
  });
});
