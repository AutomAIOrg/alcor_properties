import { Component, OnDestroy, OnInit, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { Role } from '../../models/user.model';
import {
  ApartmentCreateRequest,
  ApartmentResponse,
  ApartmentService,
  ApartmentUpdateRequest,
} from '../../services/apartment.service';
import {
  AdminUserResponse,
  AdminUserSaveRequest,
  AdminUserService,
} from '../../services/admin-user.service';

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
  reference: string;
  name: string;
  address: string;
}

interface AdminPropertyDraft {
  apartment_id: string;
  community: string;
  apartment_description: string;
  address: string;
  rooms: number;
  bathrooms: number;
  parking: string;
  total_occupants: number;
  owner_name: string;
  email: string;
  phone: string;
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
  private apartmentService = inject(ApartmentService);
  private toastTimeout: ReturnType<typeof setTimeout> | null = null;

  readonly roleOptions: Role[] = ['admin', 'limpiadora'];

  users = signal<AdminUserRow[]>([]);
  isLoadingUsers = signal(false);
  isSavingUser = signal(false);
  isDeletingUser = signal(false);
  usersError = signal<string | null>(null);
  editingUserId = signal<number | null>(null);
  isUserFormModalOpen = signal(false);
  userPendingDeletion = signal<AdminUserRow | null>(null);
  isPropertyFormModalOpen = signal(false);
  isSavingProperty = signal(false);
  isDeletingProperty = signal(false);
  editingPropertyReference = signal<string | null>(null);
  propertyPendingDeletion = signal<AdminPropertyRow | null>(null);
  toast = signal<ToastMessage | null>(null);

  properties = signal<AdminPropertyRow[]>([]);
  apartments = signal<ApartmentResponse[]>([]);
  isLoadingProperties = signal(false);
  propertiesError = signal<string | null>(null);

  isUsersSectionOpen = signal(false);
  isPropertiesSectionOpen = signal(false);

  newUser = signal<AdminUserDraft>({
    username: '',
    name: '',
    lastname: '',
    email: '',
    role: 'limpiadora',
  });

  newProperty = signal<AdminPropertyDraft>(this.createEmptyPropertyDraft());

  ngOnInit(): void {
    this.loadUsers();
    this.loadProperties();
  }

  loadProperties(): void {
    this.isLoadingProperties.set(true);
    this.propertiesError.set(null);

    this.apartmentService.getAllApartments().subscribe({
      next: apartments => {
        this.apartments.set(apartments);
        this.properties.set(apartments.map(apartment => this.toPropertyRow(apartment)));
        this.isLoadingProperties.set(false);
      },
      error: () => {
        this.properties.set([]);
        this.propertiesError.set('No se han podido cargar los apartamentos desde la API.');
        this.isLoadingProperties.set(false);
      },
    });
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

  updateNewPropertyApartmentId(apartmentId: string): void {
    this.newProperty.update(property => ({ ...property, apartment_id: apartmentId }));
  }

  updateNewPropertyCommunity(community: string): void {
    this.newProperty.update(property => ({ ...property, community }));
  }

  updateNewPropertyDescription(description: string): void {
    this.newProperty.update(property => ({ ...property, apartment_description: description }));
  }

  updateNewPropertyAddress(address: string): void {
    this.newProperty.update(property => ({ ...property, address }));
  }

  updateNewPropertyRooms(rooms: number | string): void {
    this.newProperty.update(property => ({ ...property, rooms: this.toNonNegativeNumber(rooms) }));
  }

  updateNewPropertyBathrooms(bathrooms: number | string): void {
    this.newProperty.update(property => ({
      ...property,
      bathrooms: this.toNonNegativeNumber(bathrooms),
    }));
  }

  updateNewPropertyParking(parking: string): void {
    this.newProperty.update(property => ({ ...property, parking }));
  }

  updateNewPropertyTotalOccupants(totalOccupants: number | string): void {
    this.newProperty.update(property => ({
      ...property,
      total_occupants: this.toNonNegativeNumber(totalOccupants),
    }));
  }

  updateNewPropertyOwnerName(ownerName: string): void {
    this.newProperty.update(property => ({ ...property, owner_name: ownerName }));
  }

  updateNewPropertyEmail(email: string): void {
    this.newProperty.update(property => ({ ...property, email }));
  }

  updateNewPropertyPhone(phone: string): void {
    this.newProperty.update(property => ({ ...property, phone }));
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
    if (!draft.apartment_id.trim()) return;

    this.isSavingProperty.set(true);

    const editingReference = this.editingPropertyReference();
    const request$ =
      editingReference === null
        ? this.apartmentService.createApartment(this.buildApartmentCreatePayload(draft))
        : this.apartmentService.updateApartment(
            editingReference,
            this.buildApartmentUpdatePayload(draft)
          );

    request$.subscribe({
      next: response => {
        this.resetPropertyForm();
        this.isPropertyFormModalOpen.set(false);
        this.isSavingProperty.set(false);
        this.showToast('success', response.message);
        this.loadProperties();
      },
      error: (error: HttpErrorResponse) => {
        this.showToast(
          'error',
          editingReference === null
            ? 'Error al crear el apartamento.'
            : 'Error al actualizar el apartamento.',
          this.getApiErrorMessage(error)
        );
        this.isSavingProperty.set(false);
      },
    });
  }

  startEditingProperty(property: AdminPropertyRow): void {
    const apartment = this.apartments().find(item => item.apartment_id === property.reference);
    if (!apartment) return;

    this.editingPropertyReference.set(property.reference);
    this.newProperty.set({
      apartment_id: apartment.apartment_id,
      community: apartment.community ?? '',
      apartment_description: apartment.apartment_description ?? '',
      address: apartment.address ?? '',
      rooms: apartment.rooms,
      bathrooms: apartment.bathrooms,
      parking: apartment.parking,
      total_occupants: apartment.total_occupants,
      owner_name: apartment.owner_name ?? '',
      email: apartment.email ?? '',
      phone: apartment.phone ?? '',
    });
    this.isPropertyFormModalOpen.set(true);
  }

  openDeletePropertyDialog(property: AdminPropertyRow): void {
    this.propertyPendingDeletion.set(property);
  }

  closeDeletePropertyDialog(): void {
    if (this.isDeletingProperty()) return;
    this.propertyPendingDeletion.set(null);
  }

  confirmDeleteProperty(): void {
    const property = this.propertyPendingDeletion();
    if (!property) return;

    this.isDeletingProperty.set(true);

    this.apartmentService.deleteApartment(property.reference).subscribe({
      next: response => {
        if (this.editingPropertyReference() === property.reference) {
          this.resetPropertyForm();
          this.isPropertyFormModalOpen.set(false);
        }
        this.propertyPendingDeletion.set(null);
        this.isDeletingProperty.set(false);
        this.showToast('success', response.message);
        this.loadProperties();
      },
      error: (error: HttpErrorResponse) => {
        this.showToast(
          'error',
          'Error al eliminar el apartamento.',
          this.getApiErrorMessage(error)
        );
        this.isDeletingProperty.set(false);
      },
    });
  }

  closePropertyFormDialog(): void {
    if (this.isSavingProperty()) return;
    this.resetPropertyForm();
    this.isPropertyFormModalOpen.set(false);
  }

  private toPropertyRow(apartment: ApartmentResponse): AdminPropertyRow {
    const description = apartment.apartment_description?.trim();

    return {
      reference: apartment.apartment_id,
      name: description || apartment.apartment_id,
      address: apartment.address?.trim() || 'Sin dirección',
    };
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

  private buildApartmentCreatePayload(draft: AdminPropertyDraft): ApartmentCreateRequest {
    return {
      apartment_id: draft.apartment_id.trim(),
      community: draft.community.trim() || null,
      apartment_description: draft.apartment_description.trim() || null,
      address: draft.address.trim() || null,
      rooms: draft.rooms,
      bathrooms: draft.bathrooms,
      parking: draft.parking.trim() || 'N/A',
      total_occupants: draft.total_occupants,
      owner_name: draft.owner_name.trim() || null,
      email: draft.email.trim() || null,
      phone: draft.phone.trim() || null,
    };
  }

  private buildApartmentUpdatePayload(draft: AdminPropertyDraft): ApartmentUpdateRequest {
    return {
      community: draft.community.trim() || null,
      apartment_description: draft.apartment_description.trim() || null,
      address: draft.address.trim() || null,
      rooms: draft.rooms,
      bathrooms: draft.bathrooms,
      parking: draft.parking.trim() || 'N/A',
      total_occupants: draft.total_occupants,
      owner_name: draft.owner_name.trim() || null,
      email: draft.email.trim() || null,
      phone: draft.phone.trim() || null,
    };
  }

  private createEmptyPropertyDraft(): AdminPropertyDraft {
    return {
      apartment_id: '',
      community: '',
      apartment_description: '',
      address: '',
      rooms: 0,
      bathrooms: 0,
      parking: 'N/A',
      total_occupants: 0,
      owner_name: '',
      email: '',
      phone: '',
    };
  }

  private toNonNegativeNumber(value: number | string): number {
    const parsed = typeof value === 'number' ? value : Number(value);
    return Number.isFinite(parsed) && parsed >= 0 ? parsed : 0;
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
    this.editingPropertyReference.set(null);
    this.newProperty.set(this.createEmptyPropertyDraft());
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
