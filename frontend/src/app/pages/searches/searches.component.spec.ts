import { Component, EventEmitter, Input, Output } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';

import { Apartment } from '../../models/apartment.model';
import { Booking } from '../../models/booking.model';
import { ApartmentService } from '../../services/apartment.service';
import {
  BookingCreateInitialValues,
  BookingCreateModalComponent,
} from '../../shared/components/booking-create-modal/booking-create-modal.component';
import { BookingModalComponent } from '../../shared/components/booking-modal/booking-modal.component';
import { SearchesComponent } from './searches.component';
import {
  ApartmentLoadRequest,
  ApartmentSearchComponent,
} from './components/apartment-search/apartment-search.component';
import {
  AvailabilityBookingCreateRequest,
  AvailabilitySearchComponent,
} from './components/availability-search/availability-search.component';
import { BookingSearchComponent } from './components/booking-search/booking-search.component';

@Component({
  selector: 'app-availability-search',
  standalone: true,
  template: '',
})
class StubAvailabilitySearchComponent {
  @Output() apartmentSelected = new EventEmitter<Apartment>();
  @Output() bookingCreateRequested = new EventEmitter<AvailabilityBookingCreateRequest>();

  searchAvailabilityIfDatesReady = jest.fn();
}

@Component({
  selector: 'app-apartment-search',
  standalone: true,
  template: '',
})
class StubApartmentSearchComponent {
  @Input() allApartmentIds: string[] = [];
  @Input() apartmentToLoad: ApartmentLoadRequest | null = null;
  @Output() bookingSelected = new EventEmitter<Booking>();

  refreshAfterBookingSaved = jest.fn();
}

@Component({
  selector: 'app-booking-search',
  standalone: true,
  template: '',
})
class StubBookingSearchComponent {
  @Input() allApartmentIds: string[] = [];
  @Output() bookingSelected = new EventEmitter<Booking>();

  refreshAfterBookingSaved = jest.fn();
}

@Component({
  selector: 'app-booking-modal',
  standalone: true,
  template: '',
})
class StubBookingModalComponent {
  @Input() booking!: Booking;
  @Output() close = new EventEmitter<void>();
  @Output() saved = new EventEmitter<Booking>();
}

@Component({
  selector: 'app-booking-create-modal',
  standalone: true,
  template: '',
})
class StubBookingCreateModalComponent {
  @Input() apartments: string[] = [];
  @Input() initialValues: BookingCreateInitialValues | null = null;
  @Output() close = new EventEmitter<void>();
  @Output() created = new EventEmitter<Booking>();
}

function makeApartment(overrides: Partial<Apartment> = {}): Apartment {
  return {
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
    ...overrides,
  };
}

function makeBooking(overrides: Partial<Booking> = {}): Booking {
  return {
    record_id: 1,
    apartment_id: 'R101',
    guest_name: 'Laura Garcia',
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

describe('SearchesComponent', () => {
  let fixture: ComponentFixture<SearchesComponent>;
  let component: SearchesComponent;
  let apartmentServiceSpy: jest.Mocked<ApartmentService>;

  beforeEach(async () => {
    apartmentServiceSpy = {
      getAllApartmentIds: jest.fn().mockReturnValue(of(['R101', 'R202'])),
    } as unknown as jest.Mocked<ApartmentService>;

    await TestBed.configureTestingModule({
      imports: [SearchesComponent],
      providers: [{ provide: ApartmentService, useValue: apartmentServiceSpy }],
    })
      .overrideComponent(SearchesComponent, {
        remove: {
          imports: [
            BookingModalComponent,
            BookingCreateModalComponent,
            AvailabilitySearchComponent,
            ApartmentSearchComponent,
            BookingSearchComponent,
          ],
        },
        add: {
          imports: [
            StubBookingModalComponent,
            StubBookingCreateModalComponent,
            StubAvailabilitySearchComponent,
            StubApartmentSearchComponent,
            StubBookingSearchComponent,
          ],
        },
      })
      .compileComponents();

    fixture = TestBed.createComponent(SearchesComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('inicia en la pestana de disponibilidad', () => {
    expect(component.activeTab()).toBe('availability');
    expect(apartmentServiceSpy.getAllApartmentIds).not.toHaveBeenCalled();
  });

  it('cambia de tab y carga IDs de pisos bajo demanda solo una vez', () => {
    component.selectTab('apartment');
    component.selectTab('bookings');

    expect(component.activeTab()).toBe('bookings');
    expect(apartmentServiceSpy.getAllApartmentIds).toHaveBeenCalledTimes(1);
    expect(component.allApartmentIds()).toEqual(['R101', 'R202']);
    expect(component.loadingApartmentIds()).toBe(false);
  });

  it('muestra error si falla la carga de IDs', () => {
    apartmentServiceSpy.getAllApartmentIds.mockReturnValue(throwError(() => new Error('network')));

    component.selectTab('apartment');
    fixture.detectChanges();

    expect(component.allApartmentIds()).toEqual([]);
    expect(component.apartmentIdsError()).toBe('No se pudieron cargar los pisos.');
    expect(fixture.nativeElement.querySelector('.page-error')?.textContent).toContain(
      'No se pudieron cargar los pisos.'
    );
  });

  it('abre detalle de piso desde disponibilidad y cambia a la pestana de piso', () => {
    const availabilityEl = fixture.debugElement.query(
      el => el.nativeElement.tagName === 'APP-AVAILABILITY-SEARCH'
    );
    const apartment = makeApartment({ apartment_id: 'R303' });

    (availabilityEl.componentInstance as StubAvailabilitySearchComponent).apartmentSelected.emit(
      apartment
    );
    fixture.detectChanges();

    expect(component.activeTab()).toBe('apartment');
    expect(component.apartmentToLoad()).toEqual({ apartmentId: 'R303', requestId: 1 });
  });

  it('abre y cierra modal de reserva desde la busqueda de reservas', () => {
    const booking = makeBooking({ record_id: 7 });
    const bookingSearchEl = fixture.debugElement.query(
      el => el.nativeElement.tagName === 'APP-BOOKING-SEARCH'
    );

    (bookingSearchEl.componentInstance as StubBookingSearchComponent).bookingSelected.emit(booking);
    fixture.detectChanges();

    expect(component.selectedBooking()).toEqual(booking);
    const modalEl = fixture.debugElement.query(
      el => el.nativeElement.tagName === 'APP-BOOKING-MODAL'
    );
    expect((modalEl.componentInstance as StubBookingModalComponent).booking).toEqual(booking);

    (modalEl.componentInstance as StubBookingModalComponent).close.emit();
    fixture.detectChanges();

    expect(component.selectedBooking()).toBeNull();
  });

  it('abre y cierra modal de creacion con valores iniciales desde disponibilidad', () => {
    const availabilityEl = fixture.debugElement.query(
      el => el.nativeElement.tagName === 'APP-AVAILABILITY-SEARCH'
    );
    const request: AvailabilityBookingCreateRequest = {
      apartment: makeApartment({ apartment_id: 'R404' }),
      checkIn: '2025-08-01',
      checkOut: '2025-08-05',
    };

    (
      availabilityEl.componentInstance as StubAvailabilitySearchComponent
    ).bookingCreateRequested.emit(request);
    fixture.detectChanges();

    expect(apartmentServiceSpy.getAllApartmentIds).toHaveBeenCalledTimes(1);
    expect(component.createBookingInitialValues()).toEqual({
      apartment_id: 'R404',
      check_in: '2025-08-01',
      check_out: '2025-08-05',
    });
    const createModalEl = fixture.debugElement.query(
      el => el.nativeElement.tagName === 'APP-BOOKING-CREATE-MODAL'
    );
    expect((createModalEl.componentInstance as StubBookingCreateModalComponent).apartments).toEqual(
      ['R101', 'R202']
    );

    (createModalEl.componentInstance as StubBookingCreateModalComponent).close.emit();
    fixture.detectChanges();

    expect(component.createBookingInitialValues()).toBeNull();
  });

  it('propaga refrescos a hijos tras crear reserva', () => {
    const availabilitySearch = { searchAvailabilityIfDatesReady: jest.fn() };
    const apartmentSearch = { refreshAfterBookingSaved: jest.fn() };
    const bookingSearch = { refreshAfterBookingSaved: jest.fn() };
    const created = makeBooking({ record_id: 11 });

    Object.assign(component as unknown as Record<string, unknown>, {
      availabilitySearch,
      apartmentSearch,
      bookingSearch,
    });
    component.createBookingInitialValues.set({
      apartment_id: 'R101',
      check_in: '2025-07-01',
      check_out: '2025-07-05',
    });

    component.onBookingCreated(created);

    expect(component.createBookingInitialValues()).toBeNull();
    expect(availabilitySearch.searchAvailabilityIfDatesReady).toHaveBeenCalledTimes(1);
    expect(apartmentSearch.refreshAfterBookingSaved).toHaveBeenCalledWith(created);
    expect(bookingSearch.refreshAfterBookingSaved).toHaveBeenCalledWith(created);
  });

  it('propaga refrescos a hijos tras editar reserva y mantiene el modal actualizado', () => {
    const apartmentSearch = { refreshAfterBookingSaved: jest.fn() };
    const bookingSearch = { refreshAfterBookingSaved: jest.fn() };
    const updated = makeBooking({ record_id: 12, guest_name: 'Actualizada' });

    Object.assign(component as unknown as Record<string, unknown>, {
      apartmentSearch,
      bookingSearch,
    });

    component.onBookingSaved(updated);

    expect(apartmentSearch.refreshAfterBookingSaved).toHaveBeenCalledWith(updated);
    expect(bookingSearch.refreshAfterBookingSaved).toHaveBeenCalledWith(updated);
    expect(component.selectedBooking()).toEqual(updated);
  });
});
