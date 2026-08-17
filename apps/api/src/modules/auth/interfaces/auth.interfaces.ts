export interface JwtPayload {
  sub: string;
  email: string;
  schoolId?: string;
  roles: string[];
  permissions: string[];
  iat?: number;
  exp?: number;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
}

export interface AuthResponse {
  tokens: AuthTokens;
  user: {
    id: string;
    email: string;
    firstName: string;
    lastName: string;
    avatar?: string;
    roles: string[];
    permissions: string[];
    school?: {
      id: string;
      name: string;
      slug: string;
    };
  };
}
