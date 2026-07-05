export type Role = 'admin' | 'limpiadora';

export type Permission =
  | 'calendar:access'
  | 'cleaning:access'
  | 'bookings:read'
  | 'bookings:create'
  | 'bookings:update'
  | 'bookings:delete'
  | 'searches:access'
  | 'admin:access'
  | 'users:manage'
  | 'properties:manage'
  | 'bills:read'
  | 'bills:create'
  | 'bills:update'
  | 'settings:read'
  | 'settings:manage';

export interface User {
  sub: string;
  username: string;
  name: string;
  role: Role;
  exp: number;
  iat: number;
}
