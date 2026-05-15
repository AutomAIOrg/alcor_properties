// Respuesta que devuelve el backend al hacer login correctamente
export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  role: string;
}

// Payload que se envía al backend para hacer login
export interface AuthRequest {
  username: string;
  password: string;
}

// Payload decodificado del JWT (coincide con lo que genera el backend)
export interface JwtPayload {
  sub: string;
  username: string;
  name: string;
  role: string;
  iat: number;
  exp: number;
}