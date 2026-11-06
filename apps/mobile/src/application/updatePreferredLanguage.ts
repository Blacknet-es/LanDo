import type { ApiClient } from '@shared/api/client';
import type { AppLanguage } from '@shared/i18n';
import type { UserProfileResponse } from '@shared/types/auth';

type LanguageApi = Pick<ApiClient, 'updatePreferredLanguage'>;

export function updatePreferredLanguage(
  api: LanguageApi,
  language: AppLanguage,
): Promise<UserProfileResponse> {
  return api.updatePreferredLanguage(language);
}
