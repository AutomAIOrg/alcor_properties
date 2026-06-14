import { Role, Permission } from '../models/user.model';

export const ROLE_PERMISSIONS: Record<Role, Permission[]> = {
  admin: [
    'calendar:access',
    'cleaning:access',
    'bookings:read',
    'bookings:create',
    'bookings:update',
    'bookings:delete',
    'searches:access',
    'admin:access',
    'users:manage',
    'properties:manage',
  ],
  limpiadora: ['cleaning:access', 'bookings:read'], //Revisar permisos
};
