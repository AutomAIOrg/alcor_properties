import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';

import { AdminComponent } from './admin.component';
import { AuthService } from '../../auth/auth.service';
import { Role } from '../../models/user.model';
import { ApartmentResponse, ApartmentService } from '../../services/apartment.service';
import { AdminUserResponse, AdminUserService } from '../../services/admin-user.service';
import { CleaningType, CleaningTypeService } from '../../services/cleaning-type.service';

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
    color: null,
    electric_allowance_enabled: false,
    electric_allowance_rate: 4,
    ...overrides,
  };
}

function makeCleaningType(overrides: Partial<CleaningType> = {}): CleaningType {
  return {
    cleaning_type_id: 1,
    name: 'Limpieza normal',
    hourly_rate: 15,
    active: true,
    ...overrides,
  };
}

describe('AdminComponent', () => {
  let fixture: ComponentFixture<AdminComponent>;
  let component: AdminComponent;
  let adminUserServiceSpy: jest.Mocked<AdminUserService>;
  let apartmentServiceSpy: jest.Mocked<ApartmentService>;
  let cleaningTypeServiceSpy: jest.Mocked<CleaningTypeService>;
  let authServiceSpy: jest.Mocked<AuthService>;

  async function setup(
    users: AdminUserResponse[] = [makeUser()],
    apartments: ApartmentResponse[] = [makeApartment()],
    cleaningTypes: CleaningType[] = [makeCleaningType()]
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

    cleaningTypeServiceSpy = {
      list: jest.fn().mockReturnValue(of(cleaningTypes)),
      create: jest.fn().mockReturnValue(of(cleaningTypes[0])),
      update: jest.fn().mockReturnValue(of(cleaningTypes[0])),
      delete: jest.fn().mockReturnValue(of(void 0)),
    } as unknown as jest.Mocked<CleaningTypeService>;

    authServiceSpy = {
      hasPermission: jest
        .fn()
        .mockImplementation((permission: string) => permission === 'settings:manage'),
    } as unknown as jest.Mocked<AuthService>;

    await TestBed.configureTestingModule({
      imports: [AdminComponent],
      providers: [
        { provide: AdminUserService, useValue: adminUserServiceSpy },
        { provide: ApartmentService, useValue: apartmentServiceSpy },
        { provide: CleaningTypeService, useValue: cleaningTypeServiceSpy },
        { provide: AuthService, useValue: authServiceSpy },
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
        color: null,
        electric_allowance_enabled: true,
        electric_allowance_rate: 6.5,
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
        color: null,
        electric_allowance_enabled: true,
        electric_allowance_rate: 6.5,
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
        color: null,
        electric_allowance_enabled: false,
        electric_allowance_rate: 4,
      });
      expect(component.editingPropertyReference()).toBeNull();
      expect(component.isPropertyFormModalOpen()).toBe(false);
    });

    it('editar apartamento precarga el cupo eléctrico guardado', async () => {
      await setup(
        [],
        [
          makeApartment({
            apartment_id: 'R180',
            electric_allowance_enabled: true,
            electric_allowance_rate: 6.5,
          }),
        ]
      );

      component.startEditingProperty({
        reference: 'R180',
        name: 'Apartamento R180',
        address: 'Calle Mayor 1',
      });

      expect(component.newProperty().electric_allowance_enabled).toBe(true);
      expect(component.newProperty().electric_allowance_rate).toBe(6.5);
    });

    it('guarda la tarifa del cupo eléctrico modificada por el administrador', async () => {
      await setup([], [makeApartment({ apartment_id: 'R180' })]);

      component.startEditingProperty({
        reference: 'R180',
        name: 'Apartamento R180',
        address: 'Calle Mayor 1',
      });
      component.updateNewPropertyElectricAllowanceEnabled(true);
      component.updateNewPropertyElectricAllowanceRate('7.25');
      component.saveProperty();

      expect(apartmentServiceSpy.updateApartment).toHaveBeenCalledWith(
        'R180',
        expect.objectContaining({
          electric_allowance_enabled: true,
          electric_allowance_rate: 7.25,
        })
      );
    });

    it('un importe vacío se guarda como la tarifa por defecto', async () => {
      await setup([], [makeApartment({ apartment_id: 'R180' })]);

      component.startEditingProperty({
        reference: 'R180',
        name: 'Apartamento R180',
        address: 'Calle Mayor 1',
      });
      component.updateNewPropertyElectricAllowanceRate('');
      component.updateNewPropertyElectricAllowanceEnabled(true);
      component.saveProperty();

      expect(apartmentServiceSpy.updateApartment).toHaveBeenCalledWith(
        'R180',
        expect.objectContaining({
          electric_allowance_enabled: true,
          electric_allowance_rate: 4,
        })
      );
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

  describe('F — tipos de limpieza', () => {
    it('carga los tipos al abrir la sección', async () => {
      await setup();

      component.toggleCleaningTypesSection();
      fixture.detectChanges();

      expect(cleaningTypeServiceSpy.list).toHaveBeenCalledTimes(1);
      expect(component.cleaningTypes().length).toBe(1);
      expect(fixture.nativeElement.textContent).toContain('Tipos de limpieza');
      expect(fixture.nativeElement.textContent).toContain('Limpieza normal');
    });

    it('crea un tipo de limpieza con nombre y tarifa', async () => {
      await setup();

      component.openCreateCleaningTypeDialog();
      component.newCleaningType.set({ name: '  Fin de semana  ', hourly_rate: '20', active: true });
      component.saveCleaningType();
      fixture.detectChanges();

      expect(cleaningTypeServiceSpy.create).toHaveBeenCalledWith({
        name: 'Fin de semana',
        hourly_rate: 20,
        active: true,
      });
      expect(fixture.nativeElement.textContent).toContain('Tipo de limpieza creado');
    });

    it('actualiza un tipo existente', async () => {
      await setup();

      component.startEditingCleaningType(makeCleaningType({ cleaning_type_id: 3, name: 'Normal' }));
      component.newCleaningType.set({ name: 'Renombrada', hourly_rate: '22', active: false });
      component.saveCleaningType();
      fixture.detectChanges();

      expect(cleaningTypeServiceSpy.update).toHaveBeenCalledWith(3, {
        name: 'Renombrada',
        hourly_rate: 22,
        active: false,
      });
      expect(fixture.nativeElement.textContent).toContain('Tipo de limpieza actualizado');
    });

    it('rechaza una tarifa inválida sin llamar al servicio', async () => {
      await setup();

      component.openCreateCleaningTypeDialog();
      component.newCleaningType.set({ name: 'X', hourly_rate: '-1', active: true });
      component.saveCleaningType();

      expect(cleaningTypeServiceSpy.create).not.toHaveBeenCalled();
    });

    it('elimina un tipo tras confirmar', async () => {
      await setup();

      component.openDeleteCleaningTypeDialog(makeCleaningType({ cleaning_type_id: 7 }));
      component.confirmDeleteCleaningType();
      fixture.detectChanges();

      expect(cleaningTypeServiceSpy.delete).toHaveBeenCalledWith(7);
      expect(fixture.nativeElement.textContent).toContain('Tipo de limpieza eliminado');
    });

    it('muestra error si falla al guardar', async () => {
      await setup();
      cleaningTypeServiceSpy.create.mockReturnValueOnce(
        throwError(() => ({ status: 409, error: { detail: 'El tipo ya existe' } }))
      );

      component.openCreateCleaningTypeDialog();
      component.newCleaningType.set({ name: 'Duplicado', hourly_rate: '10', active: true });
      component.saveCleaningType();
      fixture.detectChanges();

      expect(fixture.nativeElement.textContent).toContain('Error al crear el tipo de limpieza');
    });
  });
});
