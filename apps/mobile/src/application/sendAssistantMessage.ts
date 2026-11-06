import type { ApiClient } from '@shared/api/client';

type ChatApi = Pick<ApiClient, 'sendMessage'>;

export function sendAssistantMessage(
  api: ChatApi,
  message: string,
  threadId: string | undefined,
  userTimezone: string,
): Promise<{ reply: string; thread_id: string }> {
  return api.sendMessage(message, threadId, userTimezone);
}
