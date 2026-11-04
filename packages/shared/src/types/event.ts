/** Recurrence frequency options for calendar events. */
export type RecurrenceFrequency = 'none' | 'daily' | 'weekly' | 'monthly' | 'yearly';

/** Priority level for tasks and events. */
export type Priority = 'low' | 'medium' | 'high' | 'urgent';

/** A calendar event or task managed by LanDo. */
export interface Event {
  id: string;
  title: string;
  description?: string;
  startAt: string; // ISO 8601
  endAt?: string;  // ISO 8601 — omitted for all-day events
  allDay: boolean;
  location?: string;
  priority: Priority;
  tags: string[];
  recurrence: RecurrenceFrequency;
  createdAt: string;
  updatedAt: string;
}

/** Payload to create a new event. */
export interface CreateEventRequest {
  title: string;
  description?: string;
  startAt: string;
  endAt?: string;
  allDay?: boolean;
  location?: string;
  priority?: Priority;
  tags?: string[];
  recurrence?: RecurrenceFrequency;
}

/** Payload to partially update an existing event. */
export type UpdateEventRequest = Partial<CreateEventRequest>;
