-- 008_sun_events_calculated.sql
-- Transition sun_events to calculated values, remove external API dependency

-- UP MIGRATION

-- 1. Add is_calculated column to track data source
ALTER TABLE sun_events 
    ADD COLUMN IF NOT EXISTS is_calculated BOOLEAN DEFAULT true;

-- 2. Add index for efficient lookups
CREATE INDEX IF NOT EXISTS idx_sun_events_calculated 
    ON sun_events(location_id, date) 
    WHERE is_calculated = true;

-- 3. Clear existing external API data (start fresh with calculated values)
TRUNCATE TABLE sun_events;

-- 4. Update comments
COMMENT ON TABLE sun_events IS 'Sunrise, sunset, and golden hour events calculated mathematically per location';
COMMENT ON COLUMN sun_events.is_calculated IS 'True if calculated mathematically, false if from external API (legacy)';

-- DOWN MIGRATION
-- Uncomment to rollback:
-- DROP INDEX IF EXISTS idx_sun_events_calculated;
-- ALTER TABLE sun_events DROP COLUMN IF EXISTS is_calculated;
-- COMMENT ON TABLE sun_events IS 'Sunrise, sunset, and golden hour events from sunrise-sunset.org API';
