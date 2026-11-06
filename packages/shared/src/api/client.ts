import type { TokenResponse, UserProfileResponse, UserResponse } from '../types/auth';
import type { ApiEvent } from '../types/api-event';
import type { AppLanguage } from '../i18n';

export class ApiClientError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = 'ApiClientError';
  }
}

export interface ApiClient {
  register(email: string, password: string): Promise<UserResponse>;
  login(email: string, password: string): Promise<TokenResponse>;
  updatePreferredLanguage(language: AppLanguage): Promise<UserProfileResponse>;
  listEvents(signal?: AbortSignal): Promise<ApiEvent[]>;
  sendMessage(
    message: string,
    threadId?: string,
    userTimezone?: string,
  ): Promise<{ reply: string; thread_id: string }>;
}

export function createApiClient(
  baseUrl: string,
  getAccessToken: () => string | null,
  getLanguage?: () => AppLanguage,
): ApiClient {
  const root = `${baseUrl.replace(/\/$/, '')}/api/v1`;

  async function request<T>(
    path: string,
    init: RequestInit = {},
    authenticated = true,
  ): Promise<T> {
    const headers = new Headers(init.headers);
    if (getLanguage) headers.set('Accept-Language', getLanguage());
    if (init.body !== undefined) headers.set('Content-Type', 'application/json');
    const token = authenticated ? getAccessToken() : null;
    if (token) headers.set('Authorization', `Bearer ${token}`);

    const response = await fetch(`${root}${path}`, { ...init, headers });
    if (!response.ok) {
      const body = await response.text();
      let message = body;
      try {
        const parsed: unknown = JSON.parse(body);
        if (
          parsed &&
          typeof parsed === 'object' &&
          'detail' in parsed &&
          typeof parsed.detail === 'string'
        ) {
          message = parsed.detail;
        }
      } catch {
        // Keep the response body as the error message when it is not JSON.
      }
      throw new ApiClientError(
        message || `API request failed with HTTP ${response.status}`,
        response.status,
      );
    }
    return (await response.json()) as T;
  }

  return {
    register: (email, password) =>
      request<UserResponse>(
        '/auth/register',
        { method: 'POST', body: JSON.stringify({ email, password }) },
        false,
      ),
    login: (email, password) =>
      request<TokenResponse>(
        '/auth/login',
        { method: 'POST', body: JSON.stringify({ email, password }) },
        false,
      ),
    updatePreferredLanguage: (language) =>
      request<UserProfileResponse>('/users/me', {
        method: 'PATCH',
        body: JSON.stringify({ preferred_language: language }),
      }),
    listEvents: (signal) => request<ApiEvent[]>('/events', { signal }),
    sendMessage: (message, threadId, userTimezone = 'UTC') =>
      request<{ reply: string; thread_id: string }>('/chat', {
        method: 'POST',
        body: JSON.stringify({
          message,
          thread_id: threadId,
          user_timezone: userTimezone,
        }),
      }),
  };
}
