// Respuesta que devuelve el backend al hacer login correctamente
export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

// Payload que se envía al backend para hacer login
export interface AuthRequest {
  username: string;
  password: string;
}

// Respuesta genérica del backend (recuperación de contraseña, etc.)
export interface MessageResponse {
  message: string;
}

// Payload que se envía al backend para renovar el access token
export interface RefreshTokenRequest {
  refresh_token: string;
}

// Respuesta que devuelve el backend al renovar el access token
export interface AccessTokenResponse {
  access_token: string;
  token_type: string;
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
