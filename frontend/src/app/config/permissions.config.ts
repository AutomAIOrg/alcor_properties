import { Role, Permission } from '../models/user.model';

export const ROLE_PERMISSIONS: Record<Role, Permission[]> = {
  admin: [
    'bookings:read',
    'bookings:create',
    'bookings:update',
    'bookings:delete',
    'searches:access',
    'admin:access',
    'users:manage',
    'properties:manage',
  ],
  limpiadora: ['bookings:read'], //Revisar permisos
};
