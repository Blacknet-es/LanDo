export interface ApiEvent {
  id: string;
  title: string;
  description?: string | null;
  start_time: string;
  end_time?: string | null;
  is_all_day: boolean;
  source: string;
  external_id?: string | null;
  is_read_only: boolean;
  typology_id?: string | null;
  trigger_type: string;
  location_id?: string | null;
  trigger_condition?: string | null;
  energy_level: string;
  cognitive_load: number;
  dopamine_reward: string;
  created_at: string;
  updated_at: string;
}
