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
