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
  id: string;
  name: string;
  location: string;
  embedUrl: string;
  isLive: boolean;
}

// API Response Types
export interface TideEvent {
  timestamp: string;
  type: 'high' | 'low' | 'predicted';
  height_ft: number;
}

export interface TidesResponse {
  station_id: string;
  location_name: string;
  events: TideEvent[];
  next_low: TideEvent | null;
  next_high: TideEvent | null;
  current_height_ft: number | null;
  data_through: string;
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
