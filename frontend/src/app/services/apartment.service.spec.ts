import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { environment } from '../../environments/environment';
import { ApartmentResponse, ApartmentService } from './apartment.service';

function makeApartment(overrides: Partial<ApartmentResponse> = {}): ApartmentResponse {
  return {
    apartment_id: 'R180',
    community: 'Residencial Norte',
    apartment_description: 'Apartamento R180',
    address: 'Calle Mayor 1',
    rooms: 2,
    bathrooms: 1,
    parking: 'P-12',
    total_occupants: 4,
    owner_name: 'Juan Pérez',
    email: 'juan@example.com',
    phone: '+34600000000',
    ...overrides,
  };
}

describe('ApartmentService', () => {
  let service: ApartmentService;
  let httpMock: HttpTestingController;

  const API = `${environment.apiUrl}/api/v1/apartments/all`;

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
    it('hace GET al endpoint /all y devuelve la lista recibida', () => {
      const apartments = [makeApartment(), makeApartment({ apartment_id: 'R184' })];
      let result: ApartmentResponse[] | undefined;

      service.getAllApartments().subscribe(response => {
        result = response;
      });

      const req = httpMock.expectOne(API);
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

      const req = httpMock.expectOne(API);
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
});
