export interface UserProfileResponse extends UserResponse {
  preferred_language: 'en' | 'es';
}

export interface TokenResponse {
  access_token: string;
  token_type: 'bearer';
}

export interface UserResponse {
  id: string;
  email: string;
  created_at: string;
}
