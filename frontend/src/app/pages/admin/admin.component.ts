import { Component, OnDestroy, OnInit, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { Role } from '../../models/user.model';
import {
  AdminUserResponse,
  AdminUserSaveRequest,
  AdminUserService,
} from '../../services/admin-user.service';
import { BillingSettingsService } from '../../services/billing-settings.service';

type ToastType = 'success' | 'error';

interface ToastMessage {
  type: ToastType;
  text: string;
  detail?: string;
}

interface AdminUserRow {
  id: number;
  username: string;
  name: string;
  lastname: string;
  email: string | null;
  role: Role;
}

interface AdminUserDraft {
  username: string;
  name: string;
  lastname: string;
  email: string;
  role: Role;
}

interface AdminPropertyRow {
  id: number;
  reference: string;
  name: string;
  address: string;
}

interface AdminPropertyDraft {
  reference: string;
  name: string;
  address: string;
}

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './admin.component.html',
  styleUrl: './admin.component.scss',
})
export class AdminComponent implements OnInit, OnDestroy {
  private adminUserService = inject(AdminUserService);
  private billingSettingsService = inject(BillingSettingsService);
  private toastTimeout: ReturnType<typeof setTimeout> | null = null;

  readonly roleOptions: Role[] = ['admin', 'limpiadora'];

  private nextPropertyId = 4;

  users = signal<AdminUserRow[]>([]);
  isLoadingUsers = signal(false);
  isSavingUser = signal(false);
  isDeletingUser = signal(false);
  usersError = signal<string | null>(null);
  editingUserId = signal<number | null>(null);
  isUserFormModalOpen = signal(false);
  userPendingDeletion = signal<AdminUserRow | null>(null);
  editingPropertyId = signal<number | null>(null);
  isPropertyFormModalOpen = signal(false);
  propertyPendingDeletion = signal<AdminPropertyRow | null>(null);
  toast = signal<ToastMessage | null>(null);

  properties = signal<AdminPropertyRow[]>([
    {
      id: 1,
      reference: 'R180',
      name: 'Apartamento R180',
      address: 'Dirección pendiente de confirmar',
    },
    {
      id: 2,
      reference: 'R184',
      name: 'Apartamento R184',
      address: 'Dirección pendiente de confirmar',
    },
    {
      id: 3,
      reference: 'VILLA-01',
      name: 'Villa principal',
      address: 'Dirección pendiente de confirmar',
    },
  ]);

  isUsersSectionOpen = signal(false);
  isPropertiesSectionOpen = signal(false);
  isBillingSectionOpen = signal(false);

  // Gestión de facturas — precio por hora de limpieza
  private isBillingLoaded = false;
  cleaningRateDraft = signal<string>('');
  isLoadingRate = signal(false);
  isSavingRate = signal(false);
  billingError = signal<string | null>(null);

  newUser = signal<AdminUserDraft>({
    username: '',
    name: '',
    lastname: '',
    email: '',
    role: 'limpiadora',
  });

  newProperty = signal<AdminPropertyDraft>({
    reference: '',
    name: '',
    address: '',
  });

  ngOnInit(): void {
    this.loadUsers();
  }

  loadUsers(): void {
    this.isLoadingUsers.set(true);
    this.usersError.set(null);

    this.adminUserService.getUsers().subscribe({
      next: users => {
        this.users.set(users.map(user => this.toUserRow(user)));
        this.isLoadingUsers.set(false);
      },
      error: () => {
        this.users.set([]);
        this.usersError.set('No se han podido cargar los usuarios desde la API.');
        this.isLoadingUsers.set(false);
      },
    });
  }

  toggleUsersSection(): void {
    this.isUsersSectionOpen.update(isOpen => !isOpen);
  }

  togglePropertiesSection(): void {
    this.isPropertiesSectionOpen.update(isOpen => !isOpen);
  }

  toggleBillingSection(): void {
    const willOpen = !this.isBillingSectionOpen();
    this.isBillingSectionOpen.set(willOpen);
    if (willOpen && !this.isBillingLoaded) {
      this.loadCleaningRate();
    }
  }

  loadCleaningRate(): void {
    this.isLoadingRate.set(true);
    this.billingError.set(null);

    this.billingSettingsService.getCleaningRate().subscribe({
      next: response => {
        this.cleaningRateDraft.set(String(response.cleaning_hourly_rate));
        this.isBillingLoaded = true;
        this.isLoadingRate.set(false);
      },
      error: () => {
        this.billingError.set('No se ha podido cargar el precio por hora de limpieza.');
        this.isLoadingRate.set(false);
      },
    });
  }

  saveCleaningRate(): void {
    const rate = Number(this.cleaningRateDraft());
    if (!Number.isFinite(rate) || rate < 0) {
      this.showToast('error', 'Introduce un precio por hora válido (mayor o igual que 0).');
      return;
    }

    this.isSavingRate.set(true);
    this.billingError.set(null);

    this.billingSettingsService.updateCleaningRate(rate).subscribe({
      next: response => {
        this.cleaningRateDraft.set(String(response.cleaning_hourly_rate));
        this.isSavingRate.set(false);
        this.showToast('success', 'Precio por hora de limpieza actualizado.');
      },
      error: (error: HttpErrorResponse) => {
        this.showToast(
          'error',
          'No se ha podido actualizar el precio por hora.',
          this.getApiErrorMessage(error)
        );
        this.isSavingRate.set(false);
      },
    });
  }

  updateNewUserUsername(username: string): void {
    this.newUser.update(user => ({ ...user, username }));
  }

  updateNewUserName(name: string): void {
    this.newUser.update(user => ({ ...user, name }));
  }

  updateNewUserLastname(lastname: string): void {
    this.newUser.update(user => ({ ...user, lastname }));
  }

  updateNewUserEmail(email: string): void {
    this.newUser.update(user => ({ ...user, email }));
  }

  updateNewUserRole(role: Role): void {
    this.newUser.update(user => ({ ...user, role }));
  }

  updateNewPropertyReference(reference: string): void {
    this.newProperty.update(property => ({ ...property, reference }));
  }

  updateNewPropertyName(name: string): void {
    this.newProperty.update(property => ({ ...property, name }));
  }

  updateNewPropertyAddress(address: string): void {
    this.newProperty.update(property => ({ ...property, address }));
  }

  openCreateUserDialog(): void {
    this.resetUserForm();
    this.usersError.set(null);
    this.isUserFormModalOpen.set(true);
  }

  saveUser(): void {
    const draft = this.newUser();
    if (!draft.username.trim() || !draft.name.trim()) return;

    const payload: AdminUserSaveRequest = {
      username: draft.username.trim(),
      name: draft.name.trim(),
      lastname: draft.lastname.trim(),
      role: draft.role,
    };

    const email = draft.email.trim();

    if (email) payload.email = email;

    this.isSavingUser.set(true);
    this.usersError.set(null);

    const editingUserId = this.editingUserId();
    const request$ =
      editingUserId === null
        ? this.adminUserService.createUser(payload)
        : this.adminUserService.updateUser(editingUserId, payload);

    request$.subscribe({
      next: response => {
        this.resetUserForm();
        this.isUserFormModalOpen.set(false);
        this.isSavingUser.set(false);
        this.showToast('success', response.message);
        this.loadUsers();
      },
      error: (error: HttpErrorResponse) => {
        this.showToast(
          'error',
          editingUserId === null ? 'Error al crear el usuario.' : 'Error al actualizar el usuario.',
          this.getApiErrorMessage(error)
        );
        this.isSavingUser.set(false);
      },
    });
  }

  startEditingUser(user: AdminUserRow): void {
    this.editingUserId.set(user.id);
    this.newUser.set({
      username: user.username,
      name: user.name,
      lastname: user.lastname,
      email: user.email ?? '',
      role: user.role,
    });
    this.usersError.set(null);
    this.isUserFormModalOpen.set(true);
  }

  cancelEditingUser(): void {
    this.closeUserFormDialog();
  }

  closeUserFormDialog(): void {
    if (this.isSavingUser()) return;
    this.resetUserForm();
    this.isUserFormModalOpen.set(false);
  }

  openDeleteUserDialog(user: AdminUserRow): void {
    this.userPendingDeletion.set(user);
  }

  closeDeleteUserDialog(): void {
    if (this.isDeletingUser()) return;
    this.userPendingDeletion.set(null);
  }

  confirmDeleteUser(): void {
    const user = this.userPendingDeletion();
    if (!user) return;

    this.isDeletingUser.set(true);
    this.usersError.set(null);

    this.adminUserService.deleteUser(user.id).subscribe({
      next: response => {
        this.users.update(users => users.filter(existingUser => existingUser.id !== user.id));
        if (this.editingUserId() === user.id) {
          this.resetUserForm();
          this.isUserFormModalOpen.set(false);
        }
        this.userPendingDeletion.set(null);
        this.isDeletingUser.set(false);
        this.showToast('success', response.message);
      },
      error: (error: HttpErrorResponse) => {
        this.showToast('error', 'Error al eliminar el usuario.', this.getApiErrorMessage(error));
        this.isDeletingUser.set(false);
      },
    });
  }

  openCreatePropertyDialog(): void {
    this.resetPropertyForm();
    this.isPropertyFormModalOpen.set(true);
  }

  saveProperty(): void {
    const draft = this.newProperty();
    if (!draft.reference.trim() || !draft.name.trim()) return;

    const property: AdminPropertyRow = {
      id: this.editingPropertyId() ?? this.nextPropertyId++,
      reference: draft.reference.trim().toUpperCase(),
      name: draft.name.trim(),
      address: draft.address.trim() || 'Dirección pendiente de confirmar',
    };

    this.properties.update(properties =>
      this.editingPropertyId() === null
        ? [...properties, property]
        : properties.map(existingProperty =>
            existingProperty.id === property.id ? property : existingProperty
          )
    );

    this.resetPropertyForm();
    this.isPropertyFormModalOpen.set(false);
  }

  startEditingProperty(property: AdminPropertyRow): void {
    this.editingPropertyId.set(property.id);
    this.newProperty.set({
      reference: property.reference,
      name: property.name,
      address: property.address,
    });
    this.isPropertyFormModalOpen.set(true);
  }

  closePropertyFormDialog(): void {
    this.resetPropertyForm();
    this.isPropertyFormModalOpen.set(false);
  }

  openDeletePropertyDialog(property: AdminPropertyRow): void {
    this.propertyPendingDeletion.set(property);
  }

  closeDeletePropertyDialog(): void {
    this.propertyPendingDeletion.set(null);
  }

  confirmDeleteProperty(): void {
    const property = this.propertyPendingDeletion();
    if (!property) return;

    this.properties.update(properties =>
      properties.filter(existingProperty => existingProperty.id !== property.id)
    );

    if (this.editingPropertyId() === property.id) {
      this.resetPropertyForm();
      this.isPropertyFormModalOpen.set(false);
    }

    this.propertyPendingDeletion.set(null);
  }

  private toUserRow(user: AdminUserResponse): AdminUserRow {
    const lastname = user.lastname?.trim();

    return {
      id: user.id,
      username: user.username,
      name: user.name,
      lastname: lastname ?? '',
      email: user.email ?? null,
      role: user.role,
    };
  }

  private resetUserForm(): void {
    this.editingUserId.set(null);
    this.newUser.set({
      username: '',
      name: '',
      lastname: '',
      email: '',
      role: 'limpiadora',
    });
  }

  private resetPropertyForm(): void {
    this.editingPropertyId.set(null);
    this.newProperty.set({
      reference: '',
      name: '',
      address: '',
    });
  }

  ngOnDestroy(): void {
    if (this.toastTimeout) {
      clearTimeout(this.toastTimeout);
      this.toastTimeout = null;
    }
  }

  private showToast(type: ToastType, text: string, detail?: string): void {
    if (this.toastTimeout) {
      clearTimeout(this.toastTimeout);
    }

    this.toast.set({ type, text, detail });
    this.toastTimeout = setTimeout(() => {
      this.toast.set(null);
      this.toastTimeout = null;
    }, 5000);
  }

  private getApiErrorMessage(error: HttpErrorResponse): string {
    const apiError = error.error;

    if (typeof apiError?.detail === 'string') {
      return apiError.detail;
    }

    if (Array.isArray(apiError?.detail)) {
      return apiError.detail
        .map((item: { msg?: string }) => item.msg)
        .filter(Boolean)
        .join('. ');
    }

    if (typeof apiError?.message === 'string') {
      return apiError.message;
    }

    return error.message || 'La operación no se ha podido completar.';
  }
}
