import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';

import { environment } from '../../environments/environment';
import { ApartmentColorService, autoApartmentColor } from './apartment-color.service';

describe('ApartmentColorService', () => {
  let service: ApartmentColorService;
  let httpMock: HttpTestingController;

  const API = `${environment.apiUrl}/api/v1/apartments`;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [ApartmentColorService, provideHttpClient(), provideHttpClientTesting()],
    });

    service = TestBed.inject(ApartmentColorService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  describe('autoApartmentColor', () => {
    it('es determinista para el mismo apartment_id', () => {
      expect(autoApartmentColor('R180')).toBe(autoApartmentColor('R180'));
    });

    it('devuelve un color hexadecimal #RRGGBB', () => {
      expect(autoApartmentColor('R180')).toMatch(/^#[0-9a-f]{6}$/);
    });

    it('no lanza con apartment_id vacío', () => {
      expect(autoApartmentColor('')).toMatch(/^#[0-9a-f]{6}$/);
    });
  });

  describe('resolve', () => {
    it('sin override devuelve el color automático', () => {
      expect(service.resolve('R180')).toBe(autoApartmentColor('R180'));
    });

    it('con color personalizado lo devuelve en lugar del automático', () => {
      service.setFromApartments([{ apartment_id: 'R180', color: '#ff0000' }]);
      expect(service.resolve('R180')).toBe('#ff0000');
    });

    it('un apartamento con color null mantiene el color automático', () => {
      service.setFromApartments([{ apartment_id: 'R180', color: null }]);
      expect(service.resolve('R180')).toBe(autoApartmentColor('R180'));
    });
  });

  describe('ensureLoaded', () => {
    it('carga el mapa de colores una sola vez y lo aplica', () => {
      service.ensureLoaded();

      const req = httpMock.expectOne(`${API}/`);
      expect(req.request.method).toBe('GET');
      req.flush([
        { apartment_id: 'R180', color: '#123456' },
        { apartment_id: 'R106', color: null },
      ]);

      expect(service.resolve('R180')).toBe('#123456');
      expect(service.resolve('R106')).toBe(autoApartmentColor('R106'));

      // Segunda llamada: no debe volver a pedir los datos (idempotente).
      service.ensureLoaded();
      httpMock.expectNone(`${API}/`);
    });
  });
});
