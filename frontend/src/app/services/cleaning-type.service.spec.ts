import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';

import { environment } from '../../environments/environment';
import { CleaningType } from '../models/cleaning-type.model';
import { CleaningTypeService } from './cleaning-type.service';

function makeCleaningType(overrides: Partial<CleaningType> = {}): CleaningType {
  return {
    cleaning_type_id: 1,
    name: 'Limpieza normal',
    hourly_rate: 15,
    active: true,
    ...overrides,
  };
}

describe('CleaningTypeService', () => {
  let service: CleaningTypeService;
  let httpMock: HttpTestingController;

  const API = `${environment.apiUrl}/api/v1/cleaning-types`;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [CleaningTypeService, provideHttpClient(), provideHttpClientTesting()],
    });

    service = TestBed.inject(CleaningTypeService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  describe('list', () => {
    it('hace GET sin filtro por defecto', () => {
      let result: CleaningType[] | undefined;

      service.list().subscribe(response => {
        result = response;
      });

      const req = httpMock.expectOne(
        request => request.url === `${API}/` && !request.params.has('active_only')
      );
      expect(req.request.method).toBe('GET');
      req.flush([makeCleaningType()]);

      expect(result).toEqual([makeCleaningType()]);
    });

    it('añade active_only=true cuando se solicita', () => {
      service.list(true).subscribe();

      const req = httpMock.expectOne(
        request => request.url === `${API}/` && request.params.get('active_only') === 'true'
      );
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });
  });

  describe('create', () => {
    it('hace POST con el payload', () => {
      const payload = { name: 'Fin de semana', hourly_rate: 20, active: true };
      let result: CleaningType | undefined;

      service.create(payload).subscribe(response => {
        result = response;
      });

      const req = httpMock.expectOne(`${API}/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(payload);
      const created = makeCleaningType({
        cleaning_type_id: 2,
        name: 'Fin de semana',
        hourly_rate: 20,
      });
      req.flush(created);

      expect(result).toEqual(created);
    });
  });

  describe('update', () => {
    it('hace PUT al recurso con el payload', () => {
      const payload = { name: 'Renombrada', hourly_rate: 22, active: false };

      service.update(3, payload).subscribe();

      const req = httpMock.expectOne(`${API}/3`);
      expect(req.request.method).toBe('PUT');
      expect(req.request.body).toEqual(payload);
      req.flush(makeCleaningType({ cleaning_type_id: 3, ...payload }));
    });
  });

  describe('delete', () => {
    it('hace DELETE al recurso', () => {
      service.delete(5).subscribe();

      const req = httpMock.expectOne(`${API}/5`);
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
    });
  });
});
