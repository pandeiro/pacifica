-- 007_station_refactor.sql
-- Separate NOAA stations from Points of Interest, add nearest station mapping

-- UP MIGRATION

-- 1. Create noaa_stations reference table
CREATE TABLE IF NOT EXISTS noaa_stations (
    id SERIAL PRIMARY KEY,
    station_id VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    lat DECIMAL(10, 6) NOT NULL,
    lng DECIMAL(10, 6) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Add columns to locations table
ALTER TABLE locations 
    ADD COLUMN IF NOT EXISTS show_in_dropdown BOOLEAN DEFAULT true,
    ADD COLUMN IF NOT EXISTS nearest_noaa_station_id INTEGER REFERENCES noaa_stations(id);

-- 3. Populate noaa_stations with official NOAA data
INSERT INTO noaa_stations (station_id, name, lat, lng, description) VALUES
    ('9410032', 'San Clemente Island', 32.8833, -118.3167, 'NOAA tide station'),
    ('9410068', 'San Nicolas Island', 33.2333, -119.5167, 'NOAA tide station'),
    ('9410079', 'Avalon, Catalina Island', 33.35, -118.3167, 'NOAA tide station'),
    ('9410120', 'Imperial Beach', 32.5833, -117.1333, 'NOAA tide station'),
    ('9410170', 'San Diego', 32.7167, -117.1667, 'NOAA tide station'),
    ('9410230', 'La Jolla', 32.8667, -117.25, 'NOAA tide station'),
    ('9410583', 'Newport Beach', 33.6, -117.8833, 'NOAA tide station'),
    ('9410660', 'Dana Point', 33.4667, -117.7, 'NOAA tide station'),
    ('9410680', 'Long Beach', 33.7667, -118.1833, 'NOAA tide station'),
    ('9410738', 'Redondo Beach', 33.85, -118.4, 'NOAA tide station'),
    ('9410777', 'El Segundo', 33.9167, -118.4333, 'NOAA tide station'),
    ('9410840', 'Santa Monica', 34.0167, -118.5, 'NOAA tide station'),
    ('9410962', 'Bechers Bay, Santa Rosa Island', 34.0, -120.0167, 'NOAA tide station'),
    ('9410971', 'Prisoners Harbor, Santa Cruz Island', 34.0167, -119.6833, 'NOAA tide station'),
    ('9411065', 'Port Hueneme', 34.1667, -119.4, 'NOAA tide station'),
    ('9411189', 'Ventura', 34.2667, -119.2833, 'NOAA tide station'),
    ('9411340', 'Santa Barbara', 34.4, -119.6833, 'NOAA tide station'),
    ('9412110', 'Port San Luis', 35.1689, -120.7542, 'NOAA tide station at Port San Luis'),
    ('9412553', 'San Simeon', 35.65, -121.1833, 'NOAA tide station')
ON CONFLICT (station_id) DO NOTHING;

-- 4. Update locations to set nearest_noaa_station_id based on existing noaa_station_id
UPDATE locations 
SET nearest_noaa_station_id = ns.id
FROM noaa_stations ns
WHERE locations.noaa_station_id = ns.station_id;

-- 5. Hide station-only locations from dropdown
UPDATE locations 
SET show_in_dropdown = false 
WHERE slug = 'port_san_luis';

-- 6. Ensure all locations with noaa_station_id are visible in dropdown
UPDATE locations 
SET show_in_dropdown = true 
WHERE noaa_station_id IS NOT NULL 
  AND slug != 'port_san_luis';

-- DOWN MIGRATION
-- Uncomment to rollback:
-- ALTER TABLE locations DROP COLUMN IF EXISTS show_in_dropdown, DROP COLUMN IF EXISTS nearest_noaa_station_id;
-- DROP TABLE IF EXISTS noaa_stations CASCADE;
