export type Role = 'admin' | 'employee' | 'viewer';

export type Permission =
  | 'bookings:read'
  | 'bookings:create'
  | 'bookings:update'
  | 'bookings:delete'
  | 'searches:access'
  | 'admin:access';

export interface User {
  sub: string;
  username: string;
  name: string;
  role: Role;
  exp: number;
  iat: number;
}
