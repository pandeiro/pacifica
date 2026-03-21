// Types for dashboard data

export interface ActivityScore {
  activity: string;
  emoji: string;
  score: number;
  rating: 'Poor' | 'Fair' | 'Good' | 'Great' | 'Epic';
  location?: string;
  details?: string;
}

export interface Condition {
  type: string;
  value: string;
  unit?: string;
  trend?: 'up' | 'down' | 'stable';
}

export type TaxonGroup = 'whale' | 'dolphin' | 'shark' | 'pinniped' | 'bird' | 'other';

export interface SightingRecord {
  id: number;
  timestamp: string;
  sighting_date: string | null;
  species: string;
  taxon_group: TaxonGroup;
  count: number | null;
  location_id: number | null;
  location_name: string | null;
  source: string;
  source_url: string | null;
  confidence: 'high' | 'medium' | 'low';
  raw_text: string | null;
  metadata: Record<string, unknown>;
}

// Legacy type (deprecated, kept for backward compatibility)
export interface Sighting {
  id: string;
  species: string;
  emoji: string;
  location: string;
  time: string;
  count?: number;
  source: string;
  isHot?: boolean;
}

export interface TideData {
  nextLow: { time: string; height: string };
  nextHigh: { time: string; height: string };
  currentHeight?: string;
}

export interface SunData {
  sunrise: string;
  sunset: string;
  goldenHour: string;
}

export interface DriveTime {
  location: string;
  minutes: number;
  distance?: string;
}

export interface SeasonalEvent {
  name: string;
  emoji: string;
  startMonth: number;
  endMonth: number;
  category: 'migration' | 'spawning' | 'bloom' | 'season' | 'breeding' | 'tidal';
  isActive: boolean;
}

export interface LiveCam {
  id: number;
  name: string;
  location_id: number;
  location_name: string | null;
  embed_type: 'youtube' | 'iframe';
  embed_url: string;
  source_name: string;
  is_active: boolean;
  sort_order: number;
}

// API Response Types
export interface StationInfo {
  name: string;
  station_id: string;
  distance_miles: number;
  direction: string;
}

export interface TideEvent {
  timestamp: string;
  type: 'high' | 'low' | 'predicted';
  height_ft: number;
}

export interface TidesResponse {
  station_id: string;
  location_name: string;
  events: TideEvent[];
  next_tide: TideEvent | null;
  next_tide_after: TideEvent | null;
  current_height_ft: number | null;
  data_through: string;
  station_info?: StationInfo;
}

export interface SunEventsResponse {
  location_id: number;
  location_name: string;
  date: string;
  sunrise: string;
  sunset: string;
  golden_hour_morning_start: string;
  golden_hour_morning_end: string;
  golden_hour_evening_start: string;
  golden_hour_evening_end: string;
}

export interface WaterTemperatureReading {
  timestamp: string;
  temperature_f: number;
  source: string;
  source_url: string | null;
}

export interface WaterTemperatureResponse {
  location_id: number;
  location_name: string;
  current_temp_f: number | null;
  current_temp_c: number | null;
  source: string | null;
  source_url: string | null;
  last_updated: string | null;
  history: WaterTemperatureReading[];
  hours_requested: number;
  readings_count: number;
  station_info?: StationInfo;
}

export interface VisibilityHistoryItem {
  timestamp: string;
  visibility_max: number;
}

export interface VisibilityResponse {
  location_id: number;
  location_name: string;
  visibility_min: number | null;
  visibility_max: number | null;
  swell_min: number | null;
  swell_max: number | null;
  source: string | null;
  source_url: string | null;
  last_updated: string | null;
  history: VisibilityHistoryItem[];
}

export interface SightingsResponse {
  sightings: SightingRecord[];
  total: number;
  days_requested: number;
}
