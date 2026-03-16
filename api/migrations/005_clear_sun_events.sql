-- 005_clear_sun_events.sql
-- Clear all sun_events data to remove stale/bad seed data
-- The scraper will repopulate with fresh, correct data on its next run

TRUNCATE TABLE sun_events;
