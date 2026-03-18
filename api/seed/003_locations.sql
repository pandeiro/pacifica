-- 003_locations.sql
-- Point Vicente location for ACS-LA Gray Whale Census

INSERT INTO locations (name, slug, lat, lng, location_type, region, noaa_station_id, coastline_bearing, description) VALUES
    ('Point Vicente', 'point_vicente', 33.7392, -118.4156, 'beach', 'la_coast', '9410738', 225.0, 'ACS-LA Gray Whale Census observation point on Palos Verdes Peninsula')
ON CONFLICT (slug) DO NOTHING;