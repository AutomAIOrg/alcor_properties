import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';

import { Booking } from '../../../../models/booking.model';
import { BookingStatsResponse } from '../../../../models/search.model';
import { BookingService } from '../../../../services/booking.service';
import { BookingSearchComponent } from './booking-search.component';

function makeBooking(overrides: Partial<Booking> = {}): Booking {
  return {
    record_id: 1,
    apartment_id: 'R101',
    guest_name: 'Laura García',
    check_in: '2025-07-01',
    check_out: '2025-07-05',
    status: 'Confirmed',
    nights: 4,
    persons: 2,
    adults: 2,
    children: 0,
    price: 500,
    charges: null,
    electric_allowance: 20,
    email: null,
    phone: null,
    booking_number: 'BK-1',
    notes: null,
    ...overrides,
  };
}

function makeStats(overrides: Partial<BookingStatsResponse> = {}): BookingStatsResponse {
  return {
    total_bookings: 1,
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
    status_breakdown: { Confirmed: 1 },
    start_date: '2025-07-01',
    end_date: '2025-07-05',
    occupancy_pct: null,
    ...overrides,
  };
}

describe('BookingSearchComponent', () => {
  let fixture: ComponentFixture<BookingSearchComponent>;
  let component: BookingSearchComponent;
  let bookingServiceSpy: jest.Mocked<BookingService>;

  beforeEach(async () => {
    bookingServiceSpy = {
      searchBookings: jest.fn(),
      getBookingStats: jest.fn(),
    } as unknown as jest.Mocked<BookingService>;

    bookingServiceSpy.searchBookings.mockReturnValue(of([makeBooking()]));
    bookingServiceSpy.getBookingStats.mockReturnValue(of(makeStats()));

    await TestBed.configureTestingModule({
      imports: [BookingSearchComponent],
      providers: [{ provide: BookingService, useValue: bookingServiceSpy }],
    }).compileComponents();

    fixture = TestBed.createComponent(BookingSearchComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('searchBookings consulta reservas y estadísticas con filtros', () => {
    const bookings = [makeBooking({ record_id: 2 })];
    const stats = makeStats({ total_bookings: 1 });
    bookingServiceSpy.searchBookings.mockReturnValue(of(bookings));
    bookingServiceSpy.getBookingStats.mockReturnValue(of(stats));
    component.bkg.from.set('2025-07-01');
    component.bkg.to.set('2025-07-05');
    component.bkg.apartmentId.set('R101');
    component.bkg.status.set('Confirmed');
    component.bkg.guestName.set('Laura');
    component.bkg.bookingNumber.set('BK-1');

    component.searchBookings();

    const expectedFilters = {
      start_date: '2025-07-01',
      end_date: '2025-07-05',
      apartment_id: 'R101',
      status: 'Confirmed',
      guest_name: 'Laura',
      booking_number: 'BK-1',
    };
    expect(bookingServiceSpy.searchBookings).toHaveBeenCalledWith(expectedFilters);
    expect(bookingServiceSpy.getBookingStats).toHaveBeenCalledWith(expectedFilters);
    expect(component.bkg.results()).toEqual(bookings);
    expect(component.bkg.stats()).toEqual(stats);
    expect(component.bkg.loading()).toBe(false);
  });

  it('completeBookingRange actualiza fechas y lanza la búsqueda automáticamente', () => {
    component.completeBookingRange({ from: '2025-07-01', to: '2025-07-05' });

    expect(component.bkg.from()).toBe('2025-07-01');
    expect(component.bkg.to()).toBe('2025-07-05');
    expect(bookingServiceSpy.searchBookings).toHaveBeenCalledWith({
      start_date: '2025-07-01',
      end_date: '2025-07-05',
    });
    expect(bookingServiceSpy.getBookingStats).toHaveBeenCalledWith({
      start_date: '2025-07-01',
      end_date: '2025-07-05',
    });
  });

  it('guarda error si falla la búsqueda', () => {
    bookingServiceSpy.searchBookings.mockReturnValue(throwError(() => new Error('network')));
    bookingServiceSpy.getBookingStats.mockReturnValue(of(makeStats()));

    component.searchBookings();

    expect(component.bkg.results()).toEqual([]);
    expect(component.bkg.stats()).toBeNull();
    expect(component.bkg.error()).toBe('Error al buscar reservas.');
    expect(component.bkg.loading()).toBe(false);
  });

  it('clearBookings limpia filtros, resultados, estadísticas y error', () => {
    component.bkg.from.set('2025-07-01');
    component.bkg.to.set('2025-07-05');
    component.bkg.apartmentId.set('R101');
    component.bkg.status.set('Confirmed');
    component.bkg.guestName.set('Laura');
    component.bkg.bookingNumber.set('BK-1');
    component.bkg.results.set([makeBooking()]);
    component.bkg.stats.set(makeStats());
    component.bkg.error.set('Error');

    component.clearBookings();

    expect(component.bkg.from()).toBe('');
    expect(component.bkg.to()).toBe('');
    expect(component.bkg.apartmentId()).toBe('');
    expect(component.bkg.status()).toBe('');
    expect(component.bkg.guestName()).toBe('');
    expect(component.bkg.bookingNumber()).toBe('');
    expect(component.bkg.results()).toEqual([]);
    expect(component.bkg.stats()).toBeNull();
    expect(component.bkg.error()).toBe('');
  });

  it('refreshAfterBookingSaved relanza la búsqueda si hay búsqueda activa', () => {
    component.bkg.stats.set(makeStats());
    bookingServiceSpy.searchBookings.mockClear();

    component.refreshAfterBookingSaved(makeBooking({ record_id: 1, guest_name: 'Actualizada' }));

    expect(bookingServiceSpy.searchBookings).toHaveBeenCalledTimes(1);
  });

  it('applyBookingUpdate actualiza la reserva existente', () => {
    component.bkg.results.set([makeBooking({ record_id: 1, guest_name: 'Antes' })]);

    component.applyBookingUpdate(makeBooking({ record_id: 1, guest_name: 'Después' }));

    expect(component.bkg.results()[0].guest_name).toBe('Después');
  });

  it('openModal emite la reserva seleccionada', () => {
    const booking = makeBooking({ record_id: 9 });
    const emitted: Booking[] = [];
    component.bookingSelected.subscribe(value => emitted.push(value));

    component.openModal(booking);

    expect(emitted).toEqual([booking]);
  });
});
