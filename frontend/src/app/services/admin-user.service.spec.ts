import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { environment } from '../../environments/environment';
import { AdminUserResponse, AdminUserSaveRequest, AdminUserService } from './admin-user.service';

function makeUser(overrides: Partial<AdminUserResponse> = {}): AdminUserResponse {
  return {
    id: 1,
    username: 'admin',
    name: 'Admin',
    lastname: 'User',
    email: 'admin@example.com',
    role: 'admin',
    ...overrides,
  };
}

function makeSaveRequest(overrides: Partial<AdminUserSaveRequest> = {}): AdminUserSaveRequest {
  return {
    username: 'cleaner',
    name: 'Cleaner',
    lastname: 'User',
    email: 'cleaner@example.com',
    role: 'limpiadora',
    ...overrides,
  };
}

describe('AdminUserService', () => {
  let service: AdminUserService;
  let httpMock: HttpTestingController;

  const API = `${environment.apiUrl}/api/v1/users/`;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [AdminUserService, provideHttpClient(), provideHttpClientTesting()],
    });

    service = TestBed.inject(AdminUserService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  describe('A — getUsers', () => {
    it('hace GET al endpoint de usuarios y devuelve la lista recibida', () => {
      const users = [makeUser(), makeUser({ id: 2, username: 'cleaner', role: 'limpiadora' })];
      let result: AdminUserResponse[] | undefined;

      service.getUsers().subscribe(response => {
        result = response;
      });

      const req = httpMock.expectOne(API);
      expect(req.request.method).toBe('GET');

      req.flush(users);

      expect(result).toEqual(users);
    });
  });

  describe('B — createUser', () => {
    it('hace POST con el payload recibido y devuelve el mensaje de la API', () => {
      const payload = makeSaveRequest();
      let result: { message: string } | undefined;

      service.createUser(payload).subscribe(response => {
        result = response;
      });

      const req = httpMock.expectOne(API);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(payload);

      req.flush({ message: 'Usuario creado correctamente' });

      expect(result).toEqual({ message: 'Usuario creado correctamente' });
    });
  });

  describe('C — updateUser', () => {
    it('hace PUT al usuario indicado con el payload recibido', () => {
      const payload = makeSaveRequest({ name: 'Cleaner Updated' });

      service.updateUser(7, payload).subscribe();

      const req = httpMock.expectOne(`${API}7`);
      expect(req.request.method).toBe('PUT');
      expect(req.request.body).toEqual(payload);

      req.flush({ message: 'Usuario actualizado correctamente' });
    });
  });

  describe('D — deleteUser', () => {
    it('hace DELETE al usuario indicado', () => {
      let result: { message: string } | undefined;

      service.deleteUser(7).subscribe(response => {
        result = response;
      });

      const req = httpMock.expectOne(`${API}7`);
      expect(req.request.method).toBe('DELETE');

      req.flush({ message: 'Usuario eliminado correctamente' });

      expect(result).toEqual({ message: 'Usuario eliminado correctamente' });
    });
  });

  describe('EC — errores HTTP', () => {
    it('propaga errores HTTP de la API', () => {
      let errorStatus: number | undefined;

      service.getUsers().subscribe({
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
