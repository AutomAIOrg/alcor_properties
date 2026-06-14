import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';

import { AdminComponent } from './admin.component';
import { Role } from '../../models/user.model';
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

describe('AdminComponent', () => {
  let fixture: ComponentFixture<AdminComponent>;
  let component: AdminComponent;
  let adminUserServiceSpy: jest.Mocked<AdminUserService>;

  async function setup(users: AdminUserResponse[] = [makeUser()]): Promise<void> {
    jest.useFakeTimers();

    adminUserServiceSpy = {
      getUsers: jest.fn().mockReturnValue(of(users)),
      createUser: jest.fn().mockReturnValue(of({ message: 'Usuario creado correctamente' })),
      updateUser: jest.fn().mockReturnValue(of({ message: 'Usuario actualizado correctamente' })),
      deleteUser: jest.fn().mockReturnValue(of({ message: 'Usuario eliminado correctamente' })),
    } as unknown as jest.Mocked<AdminUserService>;

    await TestBed.configureTestingModule({
      imports: [AdminComponent],
      providers: [{ provide: AdminUserService, useValue: adminUserServiceSpy }],
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

  describe('D — propiedades mockeadas', () => {
    it('permite crear, editar y borrar propiedades en estado local', async () => {
      await setup([]);

      component.openCreatePropertyDialog();
      component.newProperty.set({
        reference: ' villa-02 ',
        name: ' Villa secundaria ',
        address: '',
      });
      component.saveProperty();

      const created = component.properties().find(property => property.reference === 'VILLA-02');
      expect(created).toMatchObject({
        name: 'Villa secundaria',
        address: 'Dirección pendiente de confirmar',
      });

      component.startEditingProperty(created!);
      component.updateNewPropertyName('Villa actualizada');
      component.saveProperty();

      expect(component.properties().find(property => property.id === created!.id)?.name).toBe(
        'Villa actualizada'
      );

      component.openDeletePropertyDialog(created!);
      component.confirmDeleteProperty();

      expect(component.properties().some(property => property.id === created!.id)).toBe(false);
    });
  });
});
