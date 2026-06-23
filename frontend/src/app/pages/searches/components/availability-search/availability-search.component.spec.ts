import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, Subject, throwError } from 'rxjs';

import { Apartment } from '../../../../models/apartment.model';
import { ApartmentService } from '../../../../services/apartment.service';
import { AvailabilitySearchComponent } from './availability-search.component';

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

describe('AvailabilitySearchComponent', () => {
  let fixture: ComponentFixture<AvailabilitySearchComponent>;
  let component: AvailabilitySearchComponent;
  let apartmentServiceSpy: jest.Mocked<ApartmentService>;

  beforeEach(async () => {
    apartmentServiceSpy = {
      searchApartments: jest.fn(),
    } as unknown as jest.Mocked<ApartmentService>;

    apartmentServiceSpy.searchApartments.mockReturnValue(of([makeApartment()]));

    await TestBed.configureTestingModule({
      imports: [AvailabilitySearchComponent],
      providers: [{ provide: ApartmentService, useValue: apartmentServiceSpy }],
    }).compileComponents();

    fixture = TestBed.createComponent(AvailabilitySearchComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('no busca disponibilidad si falta alguna fecha', () => {
    component.avail.from.set('2025-07-01');

    component.searchAvailability();

    expect(apartmentServiceSpy.searchApartments).not.toHaveBeenCalled();
  });

  it('completeAvailabilityRange actualiza fechas, busca y guarda resultados', () => {
    const apartments = [makeApartment({ apartment_id: 'R202' })];
    apartmentServiceSpy.searchApartments.mockReturnValue(of(apartments));
    component.avail.q.set('terraza');
    component.avail.community.set('Centro');
    component.avail.minRooms.set(2);
    component.avail.minBathrooms.set(1);
    component.avail.minOccupants.set(4);
    component.avail.parking.set('yes');

    component.completeAvailabilityRange({ from: '2025-07-01', to: '2025-07-05' });

    expect(apartmentServiceSpy.searchApartments).toHaveBeenCalledWith({
      available_from: '2025-07-01',
      available_to: '2025-07-05',
      q: 'terraza',
      community: 'Centro',
      min_rooms: 2,
      min_bathrooms: 1,
      min_occupants: 4,
      parking: 'yes',
    });
    expect(component.avail.results()).toEqual(apartments);
    expect(component.avail.loading()).toBe(false);
    expect(component.avail.error()).toBe('');
  });

  it('guarda mensaje de error si falla la búsqueda', () => {
    apartmentServiceSpy.searchApartments.mockReturnValue(throwError(() => new Error('network')));
    component.avail.from.set('2025-07-01');
    component.avail.to.set('2025-07-05');

    component.searchAvailability();

    expect(component.avail.results()).toEqual([]);
    expect(component.avail.loading()).toBe(false);
    expect(component.avail.error()).toBe('Error al cargar pisos. Comprueba los filtros.');
  });

  it('ignora una respuesta antigua si ya hay una busqueda mas reciente', () => {
    const firstSearch = new Subject<Apartment[]>();
    const secondSearch = new Subject<Apartment[]>();
    apartmentServiceSpy.searchApartments
      .mockReturnValueOnce(firstSearch.asObservable())
      .mockReturnValueOnce(secondSearch.asObservable());
    component.avail.from.set('2025-07-01');
    component.avail.to.set('2025-07-05');

    component.searchAvailability();
    component.avail.q.set('nueva');
    component.searchAvailability();

    secondSearch.next([makeApartment({ apartment_id: 'R202' })]);
    secondSearch.complete();
    firstSearch.next([makeApartment({ apartment_id: 'R101' })]);
    firstSearch.complete();

    expect(component.avail.results().map(apartment => apartment.apartment_id)).toEqual(['R202']);
    expect(component.avail.loading()).toBe(false);
    expect(component.avail.error()).toBe('');
  });

  it('ignora un error antiguo si ya hay una busqueda mas reciente en curso', () => {
    const firstSearch = new Subject<Apartment[]>();
    const secondSearch = new Subject<Apartment[]>();
    apartmentServiceSpy.searchApartments
      .mockReturnValueOnce(firstSearch.asObservable())
      .mockReturnValueOnce(secondSearch.asObservable());
    component.avail.from.set('2025-07-01');
    component.avail.to.set('2025-07-05');

    component.searchAvailability();
    component.searchAvailability();
    firstSearch.error(new Error('old network error'));

    expect(component.avail.error()).toBe('');
    expect(component.avail.loading()).toBe(true);

    secondSearch.next([makeApartment({ apartment_id: 'R202' })]);
    secondSearch.complete();

    expect(component.avail.results().map(apartment => apartment.apartment_id)).toEqual(['R202']);
    expect(component.avail.loading()).toBe(false);
  });

  it('clearAvailability limpia filtros, resultados y error', () => {
    component.avail.from.set('2025-07-01');
    component.avail.to.set('2025-07-05');
    component.avail.q.set('R101');
    component.avail.community.set('Centro');
    component.avail.minRooms.set(2);
    component.avail.minBathrooms.set(1);
    component.avail.minOccupants.set(4);
    component.avail.parking.set('yes');
    component.avail.results.set([makeApartment()]);
    component.avail.error.set('Error');

    component.clearAvailability();

    expect(component.avail.from()).toBe('');
    expect(component.avail.to()).toBe('');
    expect(component.avail.q()).toBe('');
    expect(component.avail.community()).toBe('');
    expect(component.avail.minRooms()).toBeNull();
    expect(component.avail.minBathrooms()).toBeNull();
    expect(component.avail.minOccupants()).toBeNull();
    expect(component.avail.parking()).toBeNull();
    expect(component.avail.results()).toEqual([]);
    expect(component.avail.error()).toBe('');
  });

  it('clearAvailability invalida una busqueda pendiente', () => {
    const pendingSearch = new Subject<Apartment[]>();
    apartmentServiceSpy.searchApartments.mockReturnValue(pendingSearch.asObservable());
    component.avail.from.set('2025-07-01');
    component.avail.to.set('2025-07-05');

    component.searchAvailability();
    component.clearAvailability();
    pendingSearch.next([makeApartment({ apartment_id: 'R999' })]);
    pendingSearch.complete();

    expect(component.avail.results()).toEqual([]);
    expect(component.avail.loading()).toBe(false);
    expect(component.avail.error()).toBe('');
  });

  it('selectApartment emite el apartamento seleccionado', () => {
    const apartment = makeApartment({ apartment_id: 'R303' });
    const emitted: Apartment[] = [];
    component.apartmentSelected.subscribe(value => emitted.push(value));

    component.selectApartment(apartment);

    expect(emitted).toEqual([apartment]);
  });

  it('requestBookingCreate emite apartamento y rango seleccionado', () => {
    const apartment = makeApartment({ apartment_id: 'R303' });
    const emitted: Array<{ apartment: Apartment; checkIn: string; checkOut: string }> = [];
    component.bookingCreateRequested.subscribe(value => emitted.push(value));
    component.avail.from.set('2025-07-01');
    component.avail.to.set('2025-07-05');

    component.requestBookingCreate(apartment);

    expect(emitted).toEqual([
      {
        apartment,
        checkIn: '2025-07-01',
        checkOut: '2025-07-05',
      },
    ]);
  });

  it('requestBookingCreate no emite si falta el rango completo', () => {
    const emitted: Array<{ apartment: Apartment; checkIn: string; checkOut: string }> = [];
    component.bookingCreateRequested.subscribe(value => emitted.push(value));
    component.avail.from.set('2025-07-01');

    component.requestBookingCreate(makeApartment());

    expect(emitted).toEqual([]);
  });

  it('el botón Nueva reserva de una fila emite la petición de creación', () => {
    const apartment = makeApartment({ apartment_id: 'R404' });
    const emitted: Array<{ apartment: Apartment; checkIn: string; checkOut: string }> = [];
    component.bookingCreateRequested.subscribe(value => emitted.push(value));
    component.avail.from.set('2025-07-01');
    component.avail.to.set('2025-07-05');
    component.avail.results.set([apartment]);

    fixture.detectChanges();

    const button: HTMLButtonElement = fixture.nativeElement.querySelector('.btn-inline');
    button.click();

    expect(emitted).toEqual([
      {
        apartment,
        checkIn: '2025-07-01',
        checkOut: '2025-07-05',
      },
    ]);
  });
});
