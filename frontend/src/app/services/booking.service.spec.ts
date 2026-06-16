import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';

import { BookingService } from './booking.service';
import { Booking } from '../models/booking.model';
import { environment } from '../../environments/environment';

// ─── Fixture helpers ──────────────────────────────────────────────────────────

function makeBooking(overrides: Partial<Booking> = {}): Booking {
  return {
    record_id: 1,
    apartment_id: 'R180',
    guest_name: 'Ana García',
    check_in: '2025-06-01',
    check_out: '2025-06-07',
    status: 'Confirmed',
    nights: 6,
    persons: 2,
    adults: 2,
    children: 0,
    price: 600,
    charges: null,
    electric_allowance: null,
    email: null,
    phone: null,
    booking_number: null,
    notes: null,
    ...overrides,
  };
}

function makeCreateBookingData(
  overrides: Partial<Omit<Booking, 'record_id'>> = {}
): Omit<Booking, 'record_id'> {
  const { record_id, ...data } = makeBooking({
    record_id: 999,
    ...overrides,
  });

  return data;
}

// ─── Spec ─────────────────────────────────────────────────────────────────────

describe('BookingService', () => {
  let service: BookingService;
  let httpMock: HttpTestingController;

  const API = `${environment.apiUrl}/api/v1/bookings`;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [BookingService, provideHttpClient(), provideHttpClientTesting()],
    });

    service = TestBed.inject(BookingService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  // ── A: Inicialización ───────────────────────────────────────────────────────

  describe('A — inicialización', () => {
    it('se crea correctamente', () => {
      expect(service).toBeTruthy();
    });
  });

  // ── B: getBookings ─────────────────────────────────────────────────────────

  describe('B — getBookings', () => {
    it('hace GET al endpoint de reservas y devuelve la lista recibida', () => {
      const bookings = [
        makeBooking({ record_id: 1, apartment_id: 'R180' }),
        makeBooking({ record_id: 2, apartment_id: 'R101' }),
      ];

      let result: Booking[] | undefined;

      service.getBookings().subscribe(response => {
        result = response;
      });

      const req = httpMock.expectOne(`${API}/`);

      expect(req.request.method).toBe('GET');

      req.flush(bookings);

      expect(result).toEqual(bookings);
      expect(result?.length).toBe(2);
    });

    it('devuelve un array vacío si el backend responde sin reservas', () => {
      let result: Booking[] | undefined;

      service.getBookings().subscribe(response => {
        result = response;
      });

      const req = httpMock.expectOne(`${API}/`);
      req.flush([]);

      expect(result).toEqual([]);
    });
  });

  // ── C: updateBooking ───────────────────────────────────────────────────────

  describe('B2 - getCalendarBookings', () => {
    it('hace GET a calendar-events y devuelve las reservas de extendedProps', () => {
      const booking = makeBooking({ record_id: 7, apartment_id: 'R777' });
      let result: Booking[] | undefined;

      service.getCalendarBookings('2026-06-01', 42).subscribe(response => {
        result = response;
      });

      const req = httpMock.expectOne(`${API}/calendar-events?start_date=2026-06-01&days=42`);

      expect(req.request.method).toBe('GET');

      req.flush([{ extendedProps: booking }]);

      expect(result).toEqual([booking]);
    });
  });

  describe('C — updateBooking', () => {
    it('hace PUT al endpoint de la reserva indicada y devuelve la reserva actualizada', () => {
      const recordId = 10;

      const data: Partial<Booking> = {
        status: 'Cancelled',
        notes: 'Cancelada por el cliente',
      };

      const updatedBooking = makeBooking({
        record_id: recordId,
        status: 'Cancelled',
        notes: 'Cancelada por el cliente',
      });

      let result: Booking | undefined;

      service.updateBooking(recordId, data).subscribe(response => {
        result = response;
      });

      const req = httpMock.expectOne(`${API}/${recordId}`);

      expect(req.request.method).toBe('PUT');
      expect(req.request.body).toEqual(data);

      req.flush(updatedBooking);

      expect(result).toEqual(updatedBooking);
      expect(result?.record_id).toBe(recordId);
      expect(result?.status).toBe('Cancelled');
    });

    it('permite enviar un Partial<Booking> con un único campo', () => {
      const recordId = 3;
      const data: Partial<Booking> = {
        guest_name: 'Nuevo nombre',
      };

      service.updateBooking(recordId, data).subscribe();

      const req = httpMock.expectOne(`${API}/${recordId}`);

      expect(req.request.body).toEqual({
        guest_name: 'Nuevo nombre',
      });

      req.flush(makeBooking({ record_id: recordId, guest_name: 'Nuevo nombre' }));
    });
  });

  // ── D: createBooking ───────────────────────────────────────────────────────

  describe('D — createBooking', () => {
    it('hace POST al endpoint de reservas y devuelve la reserva creada', () => {
      const data = makeCreateBookingData({
        apartment_id: 'R999',
        guest_name: 'Carlos López',
        price: 900,
      });

      const createdBooking = makeBooking({
        record_id: 99,
        ...data,
      });

      let result: Booking | undefined;

      service.createBooking(data).subscribe(response => {
        result = response;
      });

      const req = httpMock.expectOne(`${API}/`);

      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(data);

      req.flush(createdBooking);

      expect(result).toEqual(createdBooking);
      expect(result?.record_id).toBe(99);
      expect(result?.apartment_id).toBe('R999');
      expect(result?.guest_name).toBe('Carlos López');
    });

    it('el body de createBooking no incluye record_id', () => {
      const data = makeCreateBookingData();

      service.createBooking(data).subscribe();

      const req = httpMock.expectOne(`${API}/`);

      expect(req.request.body.record_id).toBeUndefined();

      req.flush(makeBooking({ record_id: 50, ...data }));
    });
  });

  // ── EC: Edge cases / errores HTTP ───────────────────────────────────────────

  describe('EC — errores HTTP', () => {
    it('propaga el error si getBookings falla', () => {
      let errorStatus: number | undefined;

      service.getBookings().subscribe({
        next: () => fail('No debería emitir una respuesta correcta'),
        error: error => {
          errorStatus = error.status;
        },
      });

      const req = httpMock.expectOne(`${API}/`);

      req.flush(
        { detail: 'Error interno' },
        {
          status: 500,
          statusText: 'Internal Server Error',
        }
      );

      expect(errorStatus).toBe(500);
    });

    it('propaga el error si updateBooking falla', () => {
      let errorStatus: number | undefined;

      service.updateBooking(1, { guest_name: 'Error' }).subscribe({
        next: () => fail('No debería emitir una respuesta correcta'),
        error: error => {
          errorStatus = error.status;
        },
      });

      const req = httpMock.expectOne(`${API}/1`);

      req.flush(
        { detail: 'Reserva no encontrada' },
        {
          status: 404,
          statusText: 'Not Found',
        }
      );

      expect(errorStatus).toBe(404);
    });

    it('propaga el error si createBooking falla', () => {
      let errorStatus: number | undefined;

      service.createBooking(makeCreateBookingData()).subscribe({
        next: () => fail('No debería emitir una respuesta correcta'),
        error: error => {
          errorStatus = error.status;
        },
      });

      const req = httpMock.expectOne(`${API}/`);

      req.flush(
        { detail: 'Datos inválidos' },
        {
          status: 422,
          statusText: 'Unprocessable Entity',
        }
      );

      expect(errorStatus).toBe(422);
    });
  });
});
