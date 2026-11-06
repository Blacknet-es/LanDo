import type { ApiClient } from '@shared/api/client';

import { mapApiEvent, type EventItem } from '../features/events/model';

type EventApi = Pick<ApiClient, 'listEvents'>;

export async function listEvents(
  api: EventApi,
  signal?: AbortSignal,
): Promise<EventItem[]> {
  const events = await api.listEvents(signal);
  return events.map(mapApiEvent);
}
