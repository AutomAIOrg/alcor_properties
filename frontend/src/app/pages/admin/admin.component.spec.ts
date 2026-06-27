import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';

import { AdminComponent } from './admin.component';
import { Role } from '../../models/user.model';
import { ApartmentResponse, ApartmentService } from '../../services/apartment.service';
import { AdminUserResponse, AdminUserService } from '../../services/admin-user.service';

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

function makeApartment(overrides: Partial<ApartmentResponse> = {}): ApartmentResponse {
  return {
    apartment_id: 'R180',
    community: null,
    apartment_description: 'Apartamento R180',
    address: 'Calle Mayor 1',
    rooms: 2,
    bathrooms: 1,
    parking: 'N/A',
    total_occupants: 4,
    owner_name: null,
    email: null,
    phone: null,
    ...overrides,
  };
}

describe('AdminComponent', () => {
  let fixture: ComponentFixture<AdminComponent>;
  let component: AdminComponent;
  let adminUserServiceSpy: jest.Mocked<AdminUserService>;
  let apartmentServiceSpy: jest.Mocked<ApartmentService>;

  async function setup(
    users: AdminUserResponse[] = [makeUser()],
    apartments: ApartmentResponse[] = [makeApartment()]
  ): Promise<void> {
    jest.useFakeTimers();

    adminUserServiceSpy = {
      getUsers: jest.fn().mockReturnValue(of(users)),
      createUser: jest.fn().mockReturnValue(of({ message: 'Usuario creado correctamente' })),
      updateUser: jest.fn().mockReturnValue(of({ message: 'Usuario actualizado correctamente' })),
      deleteUser: jest.fn().mockReturnValue(of({ message: 'Usuario eliminado correctamente' })),
    } as unknown as jest.Mocked<AdminUserService>;

    apartmentServiceSpy = {
      getAllApartments: jest.fn().mockReturnValue(of(apartments)),
      createApartment: jest
        .fn()
        .mockReturnValue(of({ message: 'Apartamento creado correctamente' })),
      updateApartment: jest
        .fn()
        .mockReturnValue(of({ message: 'Apartamento actualizado correctamente' })),
      deleteApartment: jest
        .fn()
        .mockReturnValue(of({ message: 'Apartamento eliminado correctamente' })),
    } as unknown as jest.Mocked<ApartmentService>;

    await TestBed.configureTestingModule({
      imports: [AdminComponent],
      providers: [
        { provide: AdminUserService, useValue: adminUserServiceSpy },
        { provide: ApartmentService, useValue: apartmentServiceSpy },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(AdminComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
    TestBed.resetTestingModule();
  });

  describe('A — carga de usuarios', () => {
    it('carga usuarios al iniciar y los renderiza al abrir la sección', async () => {
      await setup([
        makeUser({ id: 1, username: 'admin' }),
        makeUser({
          id: 2,
          username: 'cleaner',
          name: 'Cleaner',
          email: null,
          role: 'limpiadora',
        }),
      ]);

      expect(adminUserServiceSpy.getUsers).toHaveBeenCalledTimes(1);
      expect(component.users().length).toBe(2);
      expect(component.users()[1]).toMatchObject({
        id: 2,
        username: 'cleaner',
        email: null,
        role: 'limpiadora',
      });

      component.toggleUsersSection();
      fixture.detectChanges();

      expect(fixture.nativeElement.textContent).toContain('cleaner');
      expect(fixture.nativeElement.textContent).toContain('Sin email');
    });

    it('muestra estado de error y deja la lista vacía si falla la carga', async () => {
      await setup([]);
      adminUserServiceSpy.getUsers.mockReturnValueOnce(
        throwError(() => ({ error: { detail: 'Error interno' }, status: 500 }))
      );

      component.loadUsers();
      component.toggleUsersSection();
      fixture.detectChanges();

      expect(component.users()).toEqual([]);
      expect(component.usersError()).toBe('No se han podido cargar los usuarios desde la API.');
      expect(fixture.nativeElement.textContent).toContain('No se han podido cargar los usuarios');
    });
  });

  describe('B — guardar usuarios', () => {
    it('crear usuario envía payload trimmeado y omite email vacío', async () => {
      await setup([]);

      component.openCreateUserDialog();
      component.newUser.set({
        username: ' cleaner ',
        name: ' Cleaner ',
        lastname: ' User ',
        email: '   ',
        role: 'limpiadora',
      });

      component.saveUser();

      expect(adminUserServiceSpy.createUser).toHaveBeenCalledWith({
        username: 'cleaner',
        name: 'Cleaner',
        lastname: 'User',
        role: 'limpiadora',
      });
      expect(component.isUserFormModalOpen()).toBe(false);
      expect(component.isSavingUser()).toBe(false);
    });

    it('editar usuario llama a updateUser y cierra el modal al guardar', async () => {
      await setup([]);
      const user = {
        id: 7,
        username: 'cleaner',
        name: 'Cleaner',
        lastname: 'User',
        email: 'cleaner@example.com',
        role: 'limpiadora' as Role,
      };

      component.startEditingUser(user);
      component.updateNewUserName('Cleaner Updated');
      component.saveUser();

      expect(adminUserServiceSpy.updateUser).toHaveBeenCalledWith(7, {
        username: 'cleaner',
        name: 'Cleaner Updated',
        lastname: 'User',
        email: 'cleaner@example.com',
        role: 'limpiadora',
      });
      expect(component.editingUserId()).toBeNull();
      expect(component.isUserFormModalOpen()).toBe(false);
    });
  });

  describe('C — eliminar usuarios', () => {
    it('elimina el usuario de la lista local y cierra el modal si estaba en edición', async () => {
      await setup([]);
      const admin = {
        id: 1,
        username: 'admin',
        name: 'Admin',
        lastname: 'User',
        email: 'admin@example.com',
        role: 'admin' as Role,
      };
      const cleaner = {
        id: 2,
        username: 'cleaner',
        name: 'Cleaner',
        lastname: 'User',
        email: 'cleaner@example.com',
        role: 'limpiadora' as Role,
      };
      component.users.set([admin, cleaner]);
      component.startEditingUser(cleaner);
      component.openDeleteUserDialog(cleaner);

      component.confirmDeleteUser();

      expect(adminUserServiceSpy.deleteUser).toHaveBeenCalledWith(2);
      expect(component.users()).toEqual([admin]);
      expect(component.userPendingDeletion()).toBeNull();
      expect(component.editingUserId()).toBeNull();
      expect(component.isUserFormModalOpen()).toBe(false);
    });
  });

  describe('D — apartamentos desde API', () => {
    it('carga apartamentos al iniciar y los renderiza al abrir la sección', async () => {
      await setup(
        [],
        [
          makeApartment({ apartment_id: 'R180', apartment_description: 'Apartamento R180' }),
          makeApartment({
            apartment_id: 'R184',
            apartment_description: 'Apartamento R184',
            address: 'Calle Secundaria 2',
          }),
        ]
      );

      expect(apartmentServiceSpy.getAllApartments).toHaveBeenCalledTimes(1);
      expect(component.properties().length).toBe(2);
      expect(component.properties()[1]).toMatchObject({
        reference: 'R184',
        name: 'Apartamento R184',
        address: 'Calle Secundaria 2',
      });

      component.togglePropertiesSection();
      fixture.detectChanges();

      expect(fixture.nativeElement.textContent).toContain('R184');
      expect(fixture.nativeElement.textContent).toContain('Apartamento R184');
    });

    it('muestra estado de error y deja la lista vacía si falla la carga', async () => {
      await setup([], []);
      apartmentServiceSpy.getAllApartments.mockReturnValueOnce(
        throwError(() => ({ error: { detail: 'Error interno' }, status: 500 }))
      );

      component.loadProperties();
      component.togglePropertiesSection();
      fixture.detectChanges();

      expect(component.properties()).toEqual([]);
      expect(component.propertiesError()).toBe(
        'No se han podido cargar los apartamentos desde la API.'
      );
      expect(fixture.nativeElement.textContent).toContain(
        'No se han podido cargar los apartamentos'
      );
    });

    it('crear apartamento llama a la API y recarga el listado', async () => {
      await setup([], []);

      component.openCreatePropertyDialog();
      component.newProperty.set({
        apartment_id: ' villa-02 ',
        community: ' Residencial Sur ',
        apartment_description: ' Villa secundaria ',
        address: ' Calle Nueva 5 ',
        rooms: 3,
        bathrooms: 2,
        parking: ' P-22 ',
        total_occupants: 6,
        owner_name: ' Juan Pérez ',
        email: ' juan@example.com ',
        phone: ' 600000000 ',
      });

      component.saveProperty();

      expect(apartmentServiceSpy.createApartment).toHaveBeenCalledWith({
        apartment_id: 'villa-02',
        community: 'Residencial Sur',
        apartment_description: 'Villa secundaria',
        address: 'Calle Nueva 5',
        rooms: 3,
        bathrooms: 2,
        parking: 'P-22',
        total_occupants: 6,
        owner_name: 'Juan Pérez',
        email: 'juan@example.com',
        phone: '600000000',
      });
      expect(apartmentServiceSpy.getAllApartments).toHaveBeenCalledTimes(2);
      expect(component.isPropertyFormModalOpen()).toBe(false);
      expect(component.isSavingProperty()).toBe(false);
    });

    it('editar apartamento llama a updateApartment y cierra el modal al guardar', async () => {
      await setup(
        [],
        [
          makeApartment({
            apartment_id: 'R180',
            apartment_description: 'Apartamento R180',
            address: 'Calle Mayor 1',
            rooms: 2,
            bathrooms: 1,
          }),
        ]
      );

      const property = {
        reference: 'R180',
        name: 'Apartamento R180',
        address: 'Calle Mayor 1',
      };

      component.startEditingProperty(property);
      component.updateNewPropertyDescription('Apartamento R180 actualizado');
      component.updateNewPropertyRooms(3);
      component.saveProperty();

      expect(apartmentServiceSpy.updateApartment).toHaveBeenCalledWith('R180', {
        community: null,
        apartment_description: 'Apartamento R180 actualizado',
        address: 'Calle Mayor 1',
        rooms: 3,
        bathrooms: 1,
        parking: 'N/A',
        total_occupants: 4,
        owner_name: null,
        email: null,
        phone: null,
      });
      expect(component.editingPropertyReference()).toBeNull();
      expect(component.isPropertyFormModalOpen()).toBe(false);
    });

    it('elimina el apartamento y cierra el modal si estaba en edición', async () => {
      await setup(
        [],
        [
          makeApartment({ apartment_id: 'R180' }),
          makeApartment({ apartment_id: 'R184', apartment_description: 'Apartamento R184' }),
        ]
      );

      const r180 = { reference: 'R180', name: 'Apartamento R180', address: 'Calle Mayor 1' };
      const r184 = { reference: 'R184', name: 'Apartamento R184', address: 'Calle Mayor 1' };
      component.properties.set([r180, r184]);
      component.apartments.set([
        makeApartment({ apartment_id: 'R180' }),
        makeApartment({ apartment_id: 'R184', apartment_description: 'Apartamento R184' }),
      ]);
      component.startEditingProperty(r184);
      component.openDeletePropertyDialog(r184);

      component.confirmDeleteProperty();

      expect(apartmentServiceSpy.deleteApartment).toHaveBeenCalledWith('R184');
      expect(component.propertyPendingDeletion()).toBeNull();
      expect(component.editingPropertyReference()).toBeNull();
      expect(component.isPropertyFormModalOpen()).toBe(false);
    });
  });
});
