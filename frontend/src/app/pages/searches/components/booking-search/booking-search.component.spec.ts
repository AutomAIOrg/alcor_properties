import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, Subject, throwError } from 'rxjs';

import { Booking } from '../../../../models/booking.model';
import { BookingStatsResponse } from '../../../../models/search.model';
import { BookingService } from '../../../../services/booking.service';
import { exportBookingStatsToExcel } from '../../../../shared/utils/stats-excel-export';
import { BookingSearchComponent } from './booking-search.component';

jest.mock('../../../../shared/utils/stats-excel-export', () => ({
  exportBookingStatsToExcel: jest.fn(),
}));

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
    no_booking_days_pct: null,
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
    component.bkg.statuses.set(['Confirmed']);
    component.bkg.guestName.set('Laura');
    component.bkg.bookingNumber.set('BK-1');

    component.searchBookings();

    const expectedFilters = {
      start_date: '2025-07-01',
      end_date: '2025-07-06',
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
      end_date: '2025-07-06',
    });
    expect(bookingServiceSpy.getBookingStats).toHaveBeenCalledWith({
      start_date: '2025-07-01',
      end_date: '2025-07-06',
    });
  });

  it('searchCurrentYearBookings rellena el año actual y busca reservas', () => {
    const year = new Date().getFullYear();

    component.searchCurrentYearBookings();

    expect(component.bkg.from()).toBe(`${year}-01-01`);
    expect(component.bkg.to()).toBe(`${year}-12-31`);
    expect(bookingServiceSpy.searchBookings).toHaveBeenCalledWith({
      start_date: `${year}-01-01`,
      end_date: `${year + 1}-01-01`,
    });
    expect(bookingServiceSpy.getBookingStats).toHaveBeenCalledWith({
      start_date: `${year}-01-01`,
      end_date: `${year + 1}-01-01`,
    });
  });

  it('relanza la búsqueda automáticamente cuando cambia el filtro de ID de piso tras una búsqueda previa', () => {
    const bookings = [makeBooking({ record_id: 5, apartment_id: 'R101' })];
    const stats = makeStats({ total_bookings: 1 });
    component.bkg.results.set(bookings);
    component.bkg.stats.set(stats);

    component.onFilterChange('apartmentId', { target: { value: 'R202' } } as unknown as Event);

    expect(component.bkg.apartmentId()).toBe('R202');
    expect(bookingServiceSpy.searchBookings).toHaveBeenCalled();
    expect(bookingServiceSpy.getBookingStats).toHaveBeenCalled();
  });

  it('relanza la búsqueda automáticamente cuando cambia cualquier filtro tras una búsqueda previa', () => {
    const bookings = [makeBooking({ record_id: 6, apartment_id: 'R101' })];
    const stats = makeStats({ total_bookings: 1 });
    component.bkg.results.set(bookings);
    component.bkg.stats.set(stats);

    component.onFilterChange('guestName', { target: { value: 'Pedro' } } as unknown as Event);

    expect(component.bkg.guestName()).toBe('Pedro');
    expect(bookingServiceSpy.searchBookings).toHaveBeenCalled();
    expect(bookingServiceSpy.getBookingStats).toHaveBeenCalled();
  });

  it('muestra las reservas solapadas devueltas por el backend aunque el check-in sea anterior', () => {
    const bookings = [
      makeBooking({ record_id: 1, check_in: '2026-05-28', check_out: '2026-06-03' }),
      makeBooking({ record_id: 2, check_in: '2026-09-02', check_out: '2026-09-08' }),
    ];
    bookingServiceSpy.searchBookings.mockReturnValue(of(bookings));
    component.bkg.from.set('2026-06-01');

    component.searchBookings();

    expect(component.bkg.results()).toEqual(bookings);
  });

  it('muestra reservas aunque falle la carga de estadisticas', () => {
    const bookings = [makeBooking({ record_id: 2 })];
    bookingServiceSpy.searchBookings.mockReturnValue(of(bookings));
    bookingServiceSpy.getBookingStats.mockReturnValue(throwError(() => new Error('network')));

    component.searchBookings();

    expect(component.bkg.results()).toEqual(bookings);
    expect(component.bkg.stats()).toBeNull();
    expect(component.bkg.error()).toBe('No se pudieron cargar las estadísticas de reservas.');
    expect(component.bkg.loading()).toBe(false);
  });

  it('muestra estadisticas aunque falle la carga de reservas', () => {
    const stats = makeStats({ total_bookings: 3 });
    bookingServiceSpy.searchBookings.mockReturnValue(throwError(() => new Error('network')));
    bookingServiceSpy.getBookingStats.mockReturnValue(of(stats));

    component.searchBookings();

    expect(component.bkg.results()).toEqual([]);
    expect(component.bkg.stats()).toEqual({ ...stats, start_date: null, end_date: null });
    expect(component.bkg.error()).toBe('No se pudieron cargar las reservas.');
    expect(component.bkg.loading()).toBe(false);
  });

  it('ignora respuestas antiguas si ya hay una busqueda mas reciente', () => {
    const firstBookings = new Subject<Booking[]>();
    const firstStats = new Subject<BookingStatsResponse>();
    const secondBookings = new Subject<Booking[]>();
    const secondStats = new Subject<BookingStatsResponse>();
    bookingServiceSpy.searchBookings
      .mockReturnValueOnce(firstBookings.asObservable())
      .mockReturnValueOnce(secondBookings.asObservable());
    bookingServiceSpy.getBookingStats
      .mockReturnValueOnce(firstStats.asObservable())
      .mockReturnValueOnce(secondStats.asObservable());

    component.searchBookings();
    component.bkg.apartmentId.set('R202');
    component.searchBookings();

    secondBookings.next([makeBooking({ record_id: 2, apartment_id: 'R202' })]);
    secondBookings.complete();
    secondStats.next(makeStats({ total_bookings: 1 }));
    secondStats.complete();
    firstBookings.next([makeBooking({ record_id: 1, apartment_id: 'R101' })]);
    firstBookings.complete();
    firstStats.next(makeStats({ total_bookings: 99 }));
    firstStats.complete();

    expect(component.bkg.results().map(booking => booking.apartment_id)).toEqual(['R202']);
    expect(component.bkg.stats()?.total_bookings).toBe(1);
    expect(component.bkg.loading()).toBe(false);
  });

  it('guarda error si falla la búsqueda', () => {
    bookingServiceSpy.searchBookings.mockReturnValue(throwError(() => new Error('network')));
    bookingServiceSpy.getBookingStats.mockReturnValue(of(makeStats()));

    component.searchBookings();

    expect(component.bkg.results()).toEqual([]);
    expect(component.bkg.stats()).toEqual(makeStats({ start_date: null, end_date: null }));
    expect(component.bkg.error()).toBe('No se pudieron cargar las reservas.');
    expect(component.bkg.loading()).toBe(false);
  });

  it('clearBookings limpia filtros, resultados, estadísticas y error', () => {
    component.bkg.from.set('2025-07-01');
    component.bkg.to.set('2025-07-05');
    component.bkg.apartmentId.set('R101');
    component.bkg.statuses.set(['Confirmed']);
    component.bkg.guestName.set('Laura');
    component.bkg.bookingNumber.set('BK-1');
    component.bkg.results.set([makeBooking()]);
    component.bkg.stats.set(makeStats());
    component.bkg.error.set('Error');

    component.clearBookings();

    expect(component.bkg.from()).toBe('');
    expect(component.bkg.to()).toBe('');
    expect(component.bkg.apartmentId()).toBe('');
    expect(component.bkg.statuses()).toEqual([]);
    expect(component.bkg.guestName()).toBe('');
    expect(component.bkg.bookingNumber()).toBe('');
    expect(component.bkg.results()).toEqual([]);
    expect(component.bkg.stats()).toBeNull();
    expect(component.bkg.error()).toBe('');
  });

  it('clearBookings invalida una busqueda pendiente', () => {
    const pendingBookings = new Subject<Booking[]>();
    const pendingStats = new Subject<BookingStatsResponse>();
    bookingServiceSpy.searchBookings.mockReturnValue(pendingBookings.asObservable());
    bookingServiceSpy.getBookingStats.mockReturnValue(pendingStats.asObservable());

    component.searchBookings();
    component.clearBookings();
    pendingBookings.next([makeBooking({ record_id: 99 })]);
    pendingBookings.complete();
    pendingStats.next(makeStats({ total_bookings: 99 }));
    pendingStats.complete();

    expect(component.bkg.results()).toEqual([]);
    expect(component.bkg.stats()).toBeNull();
    expect(component.bkg.loading()).toBe(false);
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

  it('downloadStatsExcel descarga las estadisticas si existen', () => {
    const stats = makeStats();
    component.bkg.stats.set(stats);

    component.downloadStatsExcel();

    expect(exportBookingStatsToExcel).toHaveBeenCalledWith(stats);
  });
});
