import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';

import { Apartment } from '../models/apartment.model';
import { environment } from '../../environments/environment';
import { ApartmentService } from './apartment.service';

function makeApartment(overrides: Partial<Apartment> = {}): Apartment {
  return {
    apartment_id: 'R101',
    community: 'Centro',
    apartment_description: 'Apartamento familiar',
    address: 'Calle Mayor 1',
    rooms: 2,
    bathrooms: 1,
    parking: 'yes',
    total_occupants: 4,
    owner_name: 'Ana',
    email: null,
    phone: null,
    color: null,
    ...overrides,
  };
}

describe('ApartmentService', () => {
  let service: ApartmentService;
  let httpMock: HttpTestingController;

  const API = `${environment.apiUrl}/api/v1/apartments`;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [ApartmentService, provideHttpClient(), provideHttpClientTesting()],
    });

    service = TestBed.inject(ApartmentService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  describe('A — getAllApartments', () => {
    it('hace GET al endpoint /apartments y devuelve la lista recibida', () => {
      const apartments = [makeApartment(), makeApartment({ apartment_id: 'R184' })];
      let result: Apartment[] | undefined;

      service.getAllApartments().subscribe(response => {
        result = response;
      });

      const req = httpMock.expectOne(`${API}/`);
      expect(req.request.method).toBe('GET');

      req.flush(apartments);

      expect(result).toEqual(apartments);
    });
  });

  describe('B — createApartment', () => {
    it('hace POST al endpoint /apartments con el payload recibido', () => {
      const payload = makeApartment({ apartment_id: 'R184' });
      let result: { message: string } | undefined;

      service.createApartment(payload).subscribe(response => {
        result = response;
      });

      const req = httpMock.expectOne(`${environment.apiUrl}/api/v1/apartments/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(payload);

      req.flush({ message: 'Apartamento creado correctamente' });

      expect(result).toEqual({ message: 'Apartamento creado correctamente' });
    });
  });

  describe('C — updateApartment', () => {
    it('hace PUT al endpoint /{apartment_id} con el payload recibido', () => {
      const payload = {
        community: 'Residencial Norte',
        apartment_description: 'Apartamento R180 actualizado',
        address: 'Calle Mayor 1',
        rooms: 3,
        bathrooms: 2,
        parking: 'P-12',
        total_occupants: 5,
        owner_name: 'Juan Pérez',
        email: 'juan@example.com',
        phone: '+34600000000',
        color: null,
      };
      let result: { message: string } | undefined;

      service.updateApartment('R180', payload).subscribe(response => {
        result = response;
      });

      const req = httpMock.expectOne(`${environment.apiUrl}/api/v1/apartments/R180`);
      expect(req.request.method).toBe('PUT');
      expect(req.request.body).toEqual(payload);

      req.flush({ message: 'Apartamento actualizado correctamente' });

      expect(result).toEqual({ message: 'Apartamento actualizado correctamente' });
    });
  });

  describe('D — deleteApartment', () => {
    it('hace DELETE al endpoint /{apartment_id}', () => {
      let result: { message: string } | undefined;

      service.deleteApartment('R180').subscribe(response => {
        result = response;
      });

      const req = httpMock.expectOne(`${environment.apiUrl}/api/v1/apartments/R180`);
      expect(req.request.method).toBe('DELETE');

      req.flush({ message: 'Apartamento eliminado correctamente' });

      expect(result).toEqual({ message: 'Apartamento eliminado correctamente' });
    });
  });

  describe('EC — errores HTTP', () => {
    it('propaga errores HTTP de la API', () => {
      let errorStatus: number | undefined;

      service.getAllApartments().subscribe({
        next: () => fail('No debería emitir una respuesta correcta'),
        error: error => {
          errorStatus = error.status;
        },
      });

      const req = httpMock.expectOne(`${API}/`);
      req.flush(
        { detail: 'Permiso denegado' },
        {
          status: 403,
          statusText: 'Forbidden',
        }
      );

      expect(errorStatus).toBe(403);
    });
  });

  describe('E — searchApartments', () => {
    it('envia filtros como query params y respeta apartment_description', () => {
      const apartments = [makeApartment({ apartment_description: 'Terraza grande' })];
      let result: Apartment[] | undefined;

      service
        .searchApartments({
          available_from: '2026-06-01',
          available_to: '2026-06-10',
          apartment_description: 'terraza',
          min_rooms: 2,
          parking: 'yes',
        })
        .subscribe(response => {
          result = response;
        });

      const req = httpMock.expectOne(request => request.url === `${API}/search`);

      expect(req.request.method).toBe('GET');
      expect(req.request.params.get('available_from')).toBe('2026-06-01');
      expect(req.request.params.get('available_to')).toBe('2026-06-10');
      expect(req.request.params.get('apartment_description')).toBe('terraza');
      expect(req.request.params.get('min_rooms')).toBe('2');
      expect(req.request.params.get('parking')).toBe('yes');

      req.flush(apartments);

      expect(result).toEqual(apartments);
      expect(result?.[0].apartment_description).toBe('Terraza grande');
    });

    it('getAvailableApartmentIds usa available_from y available_to y devuelve IDs ordenados', () => {
      let result: string[] | undefined;

      service.getAvailableApartmentIds('2026-06-01', '2026-06-10').subscribe(response => {
        result = response;
      });

      const req = httpMock.expectOne(request => request.url === `${API}/search`);

      expect(req.request.params.get('available_from')).toBe('2026-06-01');
      expect(req.request.params.get('available_to')).toBe('2026-06-10');

      req.flush([makeApartment({ apartment_id: 'R202' }), makeApartment({ apartment_id: 'R101' })]);

      expect(result).toEqual(['R101', 'R202']);
    });

    it('getAllApartmentIds obtiene todos los pisos y filtra IDs nulos antes de ordenar', () => {
      let result: string[] | undefined;

      service.getAllApartmentIds().subscribe(response => {
        result = response;
      });

      const req = httpMock.expectOne(request => request.url === `${API}/search`);

      expect(req.request.params.keys()).toEqual([]);

      req.flush([
        makeApartment({ apartment_id: 'R202' }),
        makeApartment({ apartment_id: null as unknown as string }),
        makeApartment({ apartment_id: 'R101' }),
      ]);

      expect(result).toEqual(['R101', 'R202']);
    });

    it('getApartmentStats envia start_date y end_date al endpoint de stats', () => {
      service.getApartmentStats('R101', '2026-06-01', '2026-06-30').subscribe();

      const req = httpMock.expectOne(`${API}/stats/R101?start_date=2026-06-01&end_date=2026-06-30`);

      expect(req.request.method).toBe('GET');

      req.flush({
        apartment_id: 'R101',
        apartment: makeApartment({ apartment_id: 'R101' }),
        filtered_range: {
          start_date: '2026-06-01',
          end_date: '2026-06-30',
          total_bookings: 0,
          active_bookings: 0,
          cancelled_bookings: 0,
          cancellation_rate: null,
          total_nights: 0,
          avg_nights_per_booking: null,
          total_persons: 0,
          avg_persons_per_booking: null,
          total_revenue: null,
          avg_revenue_per_booking: null,
          avg_revenue_per_night: null,
          total_charges: null,
          total_electric_allowance: null,
          occupancy_pct: null,
          status_breakdown: {},
        },
        by_year: [],
      });
    });
  });
});
