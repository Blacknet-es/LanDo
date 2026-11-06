import type { ApiEvent } from '@shared/types/api-event';
import { translate, type AppLanguage } from '@shared/i18n';

export type Energy = 'low' | 'medium' | 'high';
export type CognitiveState = 'light' | 'moderate' | 'saturated';
export type TaskTab = 'now' | 'today' | 'geofenced';

export interface EventItem {
  id: string;
  title: string;
  description?: string | null;
  startAt: string;
  endAt?: string | null;
  energy: Energy;
  load: 1 | 2 | 3 | 4 | 5;
  priority: 'low' | 'medium' | 'high';
  location?: string | null;
  triggerType: string;
  isMicroAction: boolean;
}

export function mapApiEvent(event: ApiEvent): EventItem {
  const energy =
    event.energy_level === 'LOW_ENERGY'
      ? 'low'
      : event.energy_level === 'HIGH_ENERGY'
        ? 'high'
        : 'medium';
  const load = Math.max(1, Math.min(5, Math.round(event.cognitive_load))) as
    | 1
    | 2
    | 3
    | 4
    | 5;
  const durationMinutes = event.end_time
    ? (new Date(event.end_time).getTime() - new Date(event.start_time).getTime()) / 60_000
    : undefined;

  return {
    id: event.id,
    title: event.title,
    description: event.description,
    startAt: event.start_time,
    endAt: event.end_time,
    energy,
    load,
    priority: load >= 4 ? 'high' : load <= 2 ? 'low' : 'medium',
    location: event.location_id,
    triggerType: event.trigger_type,
    isMicroAction: durationMinutes !== undefined && durationMinutes <= 15,
  };
}

export function eventTime(value: string, language: AppLanguage = 'es'): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return translate(language, 'time_unknown');
  return date.toLocaleTimeString(language, { hour: '2-digit', minute: '2-digit' });
}

export function durationLabel(event: EventItem, language: AppLanguage = 'es'): string {
  if (!event.endAt) {
    return event.isMicroAction
      ? translate(language, 'duration_short')
      : translate(language, 'duration_flexible');
  }
  const minutes = Math.max(
    0,
    Math.round((new Date(event.endAt).getTime() - new Date(event.startAt).getTime()) / 60_000),
  );
  return minutes <= 15 ? translate(language, 'duration_short') : `${minutes} min`;
}
