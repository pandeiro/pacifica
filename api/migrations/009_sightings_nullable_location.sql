-- 009_sightings_nullable_location.sql
-- Make location_id nullable for sightings outside 30-mile radius from known locations

ALTER TABLE sightings ALTER COLUMN location_id DROP NOT NULL;