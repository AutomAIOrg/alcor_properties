import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';

import { Booking } from '../../../../models/booking.model';
import { ApartmentStatsResponse } from '../../../../models/search.model';
import { ApartmentService } from '../../../../services/apartment.service';
import { BookingService } from '../../../../services/booking.service';
import { ApartmentSearchComponent } from './apartment-search.component';

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
    booking_number: null,
    notes: null,
    ...overrides,
  };
}

function makeStats(overrides: Partial<ApartmentStatsResponse> = {}): ApartmentStatsResponse {
  return {
    apartment_id: 'R101',
    apartment: {
      apartment_id: 'R101',
      community: 'Centro',
      booking_name: null,
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
    component.apt.status.set('Confirmed');

    component.searchApartmentDetail();

    expect(bookingServiceSpy.searchBookings).toHaveBeenCalledWith({
      apartment_id: 'R202',
      start_date: '2025-07-01',
      end_date: '2025-07-05',
      status: 'Confirmed',
    });
    expect(apartmentServiceSpy.getApartmentStats).toHaveBeenCalledWith(
      'R202',
      '2025-07-01',
      '2025-07-05'
    );
    expect(component.apt.bookings()).toEqual(bookings);
    expect(component.apt.stats()).toEqual(stats);
    expect(component.apt.loading()).toBe(false);
  });

  it('apartmentToLoad carga el piso, limpia filtros y evita repetir requestId', () => {
    component.apt.from.set('2025-06-01');
    component.apt.to.set('2025-06-05');
    component.apt.status.set('Cancelled');

    fixture.componentRef.setInput('apartmentToLoad', { apartmentId: ' R303 ', requestId: 1 });
    fixture.detectChanges();

    expect(component.apt.id()).toBe('R303');
    expect(component.apt.from()).toBe('');
    expect(component.apt.to()).toBe('');
    expect(component.apt.status()).toBe('');
    expect(bookingServiceSpy.searchBookings).toHaveBeenCalledTimes(1);

    bookingServiceSpy.searchBookings.mockClear();
    apartmentServiceSpy.getApartmentStats.mockClear();

    fixture.componentRef.setInput('apartmentToLoad', { apartmentId: 'R303', requestId: 1 });
    fixture.detectChanges();

    expect(bookingServiceSpy.searchBookings).not.toHaveBeenCalled();
    expect(apartmentServiceSpy.getApartmentStats).not.toHaveBeenCalled();
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
});
