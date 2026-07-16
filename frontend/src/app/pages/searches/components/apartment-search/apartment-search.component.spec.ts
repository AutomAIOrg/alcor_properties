import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, Subject, throwError } from 'rxjs';

import { Booking } from '../../../../models/booking.model';
import { ApartmentStatsResponse, ApartmentStatsYear } from '../../../../models/search.model';
import { ApartmentService } from '../../../../services/apartment.service';
import { BookingService } from '../../../../services/booking.service';
import { exportApartmentStatsToExcel } from '../../../../shared/utils/stats-excel-export';
import { ApartmentSearchComponent } from './apartment-search.component';

jest.mock('../../../../shared/utils/stats-excel-export', () => ({
  exportApartmentStatsToExcel: jest.fn(),
}));

function makeBooking(overrides: Partial<Booking> = {}): Booking {
  return {
    record_id: 1,
    apartment_id: 'R101',
    guest_name: 'Laura García',
    check_in: '2025-07-01',
    check_out: '2025-07-05',
    check_in_time: null,
    check_out_time: null,
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
    booking_number: null,
    notes: null,
    notes_cleaning: null,
    ...overrides,
  };
}

function makeStats(overrides: Partial<ApartmentStatsResponse> = {}): ApartmentStatsResponse {
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
    filtered_range: {
      start_date: '2025-07-01',
      end_date: '2025-07-05',
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
      occupancy_pct: 100,
      status_breakdown: { Confirmed: 1 },
    },
    by_year: [],
    ...overrides,
  };
}

function makeStatsYear(overrides: Partial<ApartmentStatsYear> = {}): ApartmentStatsYear {
  return {
    year: 2025,
    total_bookings: 1,
    active_bookings: 1,
    cancelled_bookings: 0,
    cancellation_rate: 0,
    total_nights: 4,
    avg_nights_per_booking: 4,
    total_days_in_year: 365,
    occupancy_pct: 1.1,
    total_revenue: 500,
    avg_revenue_per_booking: 500,
    total_charges: null,
    total_electric_allowance: null,
    ...overrides,
  };
}

describe('ApartmentSearchComponent', () => {
  let fixture: ComponentFixture<ApartmentSearchComponent>;
  let component: ApartmentSearchComponent;
  let apartmentServiceSpy: jest.Mocked<ApartmentService>;
  let bookingServiceSpy: jest.Mocked<BookingService>;

  beforeEach(async () => {
    apartmentServiceSpy = {
      getApartmentStats: jest.fn(),
    } as unknown as jest.Mocked<ApartmentService>;
    bookingServiceSpy = {
      searchBookings: jest.fn(),
    } as unknown as jest.Mocked<BookingService>;

    apartmentServiceSpy.getApartmentStats.mockReturnValue(of(makeStats()));
    bookingServiceSpy.searchBookings.mockReturnValue(of([makeBooking()]));

    await TestBed.configureTestingModule({
      imports: [ApartmentSearchComponent],
      providers: [
        { provide: ApartmentService, useValue: apartmentServiceSpy },
        { provide: BookingService, useValue: bookingServiceSpy },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ApartmentSearchComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('searchApartmentDetail consulta reservas y estadísticas con filtros', () => {
    const bookings = [makeBooking({ record_id: 2 })];
    const stats = makeStats({ apartment_id: 'R202' });
    bookingServiceSpy.searchBookings.mockReturnValue(of(bookings));
    apartmentServiceSpy.getApartmentStats.mockReturnValue(of(stats));
    component.apt.id.set(' R202 ');
    component.apt.from.set('2025-07-01');
    component.apt.to.set('2025-07-05');

    component.searchApartmentDetail();

    expect(bookingServiceSpy.searchBookings).toHaveBeenCalledWith({
      apartment_id: 'R202',
      start_date: '2025-07-01',
      end_date: '2025-07-06',
    });
    expect(apartmentServiceSpy.getApartmentStats).toHaveBeenCalledWith(
      'R202',
      '2025-07-01',
      '2025-07-06'
    );
    expect(component.apt.bookings()).toEqual(bookings);
    expect(component.apt.stats()).toEqual({
      ...stats,
      filtered_range: {
        ...stats.filtered_range,
        start_date: '2025-07-01',
        end_date: '2025-07-05',
      },
    });
    expect(component.apt.loading()).toBe(false);
  });

  it('ordena las reservas por check-in descendente y los años de estadisticas descendentes', () => {
    const bookings = [
      makeBooking({ record_id: 1, check_in: '2025-09-01' }),
      makeBooking({ record_id: 2, check_in: '2026-10-01' }),
      makeBooking({ record_id: 3, check_in: '2026-09-01' }),
    ];
    const stats = makeStats({
      by_year: [
        makeStatsYear({ year: 2025 }),
        makeStatsYear({ year: 2026 }),
        makeStatsYear({ year: 2024 }),
      ],
    });
    bookingServiceSpy.searchBookings.mockReturnValue(of(bookings));
    apartmentServiceSpy.getApartmentStats.mockReturnValue(of(stats));
    component.apt.id.set('R202');

    component.searchApartmentDetail();

    expect(component.apt.bookings().map(booking => booking.check_in)).toEqual([
      '2026-10-01',
      '2026-09-01',
      '2025-09-01',
    ]);
    expect(component.apt.stats()?.by_year.map(yearStats => yearStats.year)).toEqual([
      2026, 2025, 2024,
    ]);
  });

  it('muestra reservas aunque falle la carga de estadisticas', () => {
    const bookings = [makeBooking({ record_id: 2 })];
    bookingServiceSpy.searchBookings.mockReturnValue(of(bookings));
    apartmentServiceSpy.getApartmentStats.mockReturnValue(throwError(() => new Error('network')));
    component.apt.id.set('R202');

    component.searchApartmentDetail();

    expect(component.apt.bookings()).toEqual(bookings);
    expect(component.apt.stats()).toBeNull();
    expect(component.apt.error()).toBe('No se pudieron cargar las estadísticas del piso.');
    expect(component.apt.loading()).toBe(false);
  });

  it('muestra estadisticas aunque falle la carga de reservas', () => {
    const stats = makeStats({ apartment_id: 'R202' });
    bookingServiceSpy.searchBookings.mockReturnValue(throwError(() => new Error('network')));
    apartmentServiceSpy.getApartmentStats.mockReturnValue(of(stats));
    component.apt.id.set('R202');

    component.searchApartmentDetail();

    expect(component.apt.bookings()).toEqual([]);
    expect(component.apt.stats()).toEqual({
      ...stats,
      filtered_range: {
        ...stats.filtered_range,
        start_date: null,
        end_date: null,
      },
    });
    expect(component.apt.error()).toBe('No se pudieron cargar las reservas del piso.');
    expect(component.apt.loading()).toBe(false);
  });

  it('ignora respuestas antiguas si ya hay una busqueda mas reciente', () => {
    const firstBookings = new Subject<Booking[]>();
    const firstStats = new Subject<ApartmentStatsResponse>();
    const secondBookings = new Subject<Booking[]>();
    const secondStats = new Subject<ApartmentStatsResponse>();
    bookingServiceSpy.searchBookings
      .mockReturnValueOnce(firstBookings.asObservable())
      .mockReturnValueOnce(secondBookings.asObservable());
    apartmentServiceSpy.getApartmentStats
      .mockReturnValueOnce(firstStats.asObservable())
      .mockReturnValueOnce(secondStats.asObservable());
    component.apt.id.set('R101');

    component.searchApartmentDetail();
    component.apt.id.set('R202');
    component.searchApartmentDetail();

    secondBookings.next([makeBooking({ record_id: 2, apartment_id: 'R202' })]);
    secondBookings.complete();
    secondStats.next(makeStats({ apartment_id: 'R202' }));
    secondStats.complete();
    firstBookings.next([makeBooking({ record_id: 1, apartment_id: 'R101' })]);
    firstBookings.complete();
    firstStats.next(makeStats({ apartment_id: 'R101' }));
    firstStats.complete();

    expect(component.apt.bookings().map(booking => booking.apartment_id)).toEqual(['R202']);
    expect(component.apt.stats()?.apartment_id).toBe('R202');
    expect(component.apt.loading()).toBe(false);
  });

  it('apartmentToLoad carga el piso, limpia filtros y evita repetir requestId', () => {
    component.apt.from.set('2025-06-01');
    component.apt.to.set('2025-06-05');

    fixture.componentRef.setInput('apartmentToLoad', { apartmentId: ' R303 ', requestId: 1 });
    fixture.detectChanges();

    expect(component.apt.id()).toBe('R303');
    expect(component.apt.from()).toBe('');
    expect(component.apt.to()).toBe('');
    expect(bookingServiceSpy.searchBookings).toHaveBeenCalledTimes(1);

    bookingServiceSpy.searchBookings.mockClear();
    apartmentServiceSpy.getApartmentStats.mockClear();

    fixture.componentRef.setInput('apartmentToLoad', { apartmentId: 'R303', requestId: 1 });
    fixture.detectChanges();

    expect(bookingServiceSpy.searchBookings).not.toHaveBeenCalled();
    expect(apartmentServiceSpy.getApartmentStats).not.toHaveBeenCalled();
  });

  it('setApartmentId lanza la busqueda automaticamente tras escribir un ID', () => {
    jest.useFakeTimers();
    bookingServiceSpy.searchBookings.mockClear();
    apartmentServiceSpy.getApartmentStats.mockClear();

    component.setApartmentId('R202');
    expect(bookingServiceSpy.searchBookings).not.toHaveBeenCalled();

    jest.advanceTimersByTime(300);

    expect(bookingServiceSpy.searchBookings).toHaveBeenCalledWith({ apartment_id: 'R202' });
    expect(apartmentServiceSpy.getApartmentStats).toHaveBeenCalledWith(
      'R202',
      undefined,
      undefined
    );

    jest.useRealTimers();
  });

  it('completeApartmentRange relanza la busqueda si ya hay ID de piso', () => {
    component.apt.id.set('R202');
    bookingServiceSpy.searchBookings.mockClear();
    apartmentServiceSpy.getApartmentStats.mockClear();

    component.completeApartmentRange({ from: '2025-07-01', to: '2025-07-05' });

    expect(bookingServiceSpy.searchBookings).toHaveBeenCalledWith({
      apartment_id: 'R202',
      start_date: '2025-07-01',
      end_date: '2025-07-06',
    });
    expect(apartmentServiceSpy.getApartmentStats).toHaveBeenCalledWith(
      'R202',
      '2025-07-01',
      '2025-07-06'
    );
  });

  it('al cerrar el calendario tras borrar fechas relanza la busqueda sin fechas', () => {
    component.apt.id.set('R202');
    component.apt.from.set('2025-07-01');
    component.apt.to.set('2025-07-05');
    component.apt.stats.set(makeStats({ apartment_id: 'R202' }));
    bookingServiceSpy.searchBookings.mockClear();
    apartmentServiceSpy.getApartmentStats.mockClear();

    component.setApartmentRange({ from: '', to: '' });
    expect(bookingServiceSpy.searchBookings).not.toHaveBeenCalled();

    component.handleApartmentCalendarClosed();

    expect(bookingServiceSpy.searchBookings).toHaveBeenCalledWith({ apartment_id: 'R202' });
    expect(apartmentServiceSpy.getApartmentStats).toHaveBeenCalledWith(
      'R202',
      undefined,
      undefined
    );
  });

  it('muestra mensaje específico si el piso no existe', () => {
    bookingServiceSpy.searchBookings.mockReturnValue(of([]));
    apartmentServiceSpy.getApartmentStats.mockReturnValue(throwError(() => ({ status: 404 })));
    component.apt.id.set('R999');

    component.searchApartmentDetail();

    expect(component.apt.error()).toBe("El piso 'R999' no existe en la base de datos.");
    expect(component.apt.loading()).toBe(false);
  });

  it('refreshAfterBookingSaved relanza la búsqueda si hay búsqueda activa', () => {
    component.apt.id.set('R101');
    component.apt.stats.set(makeStats());
    bookingServiceSpy.searchBookings.mockClear();

    component.refreshAfterBookingSaved(makeBooking({ record_id: 1, guest_name: 'Actualizada' }));

    expect(bookingServiceSpy.searchBookings).toHaveBeenCalledTimes(1);
  });

  it('applyBookingUpdate actualiza la reserva existente', () => {
    component.apt.bookings.set([makeBooking({ record_id: 1, guest_name: 'Antes' })]);

    component.applyBookingUpdate(makeBooking({ record_id: 1, guest_name: 'Después' }));

    expect(component.apt.bookings()[0].guest_name).toBe('Después');
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
    component.apt.stats.set(stats);

    component.downloadStatsExcel();

    expect(exportApartmentStatsToExcel).toHaveBeenCalledWith(stats);
  });
});
