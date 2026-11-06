import type { ApiClient } from '@shared/api/client';

type AuthenticationApi = Pick<ApiClient, 'login' | 'register'>;

export async function authenticate(
  api: AuthenticationApi,
  email: string,
  password: string,
  register: boolean,
): Promise<string> {
  if (register) await api.register(email, password);
  const { access_token: token } = await api.login(email, password);
  return token;
}
