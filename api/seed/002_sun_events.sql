-- 002_sun_events.sql
-- Seed data for sun events (stub data for development)
-- Uses subqueries to look up location IDs dynamically by slug
-- This avoids hardcoding auto-increment IDs which can change based on insertion order

INSERT INTO sun_events (date, location_id, sunrise, sunset, golden_hour_morning_start, golden_hour_morning_end, golden_hour_evening_start, golden_hour_evening_end) VALUES
    -- Dana Point
    (CURRENT_DATE, (SELECT id FROM locations WHERE slug = 'dana_point'), CURRENT_DATE + INTERVAL '6:42', CURRENT_DATE + INTERVAL '18:15', CURRENT_DATE + INTERVAL '6:12', CURRENT_DATE + INTERVAL '6:42', CURRENT_DATE + INTERVAL '17:45', CURRENT_DATE + INTERVAL '18:15'),
    (CURRENT_DATE + INTERVAL '1 day', (SELECT id FROM locations WHERE slug = 'dana_point'), CURRENT_DATE + INTERVAL '1 day 6:41', CURRENT_DATE + INTERVAL '1 day 18:16', CURRENT_DATE + INTERVAL '1 day 6:11', CURRENT_DATE + INTERVAL '1 day 6:41', CURRENT_DATE + INTERVAL '1 day 17:46', CURRENT_DATE + INTERVAL '1 day 18:16'),
    
    -- La Jolla
    (CURRENT_DATE, (SELECT id FROM locations WHERE slug = 'la_jolla'), CURRENT_DATE + INTERVAL '6:38', CURRENT_DATE + INTERVAL '18:12', CURRENT_DATE + INTERVAL '6:08', CURRENT_DATE + INTERVAL '6:38', CURRENT_DATE + INTERVAL '17:42', CURRENT_DATE + INTERVAL '18:12'),
    
    -- Santa Monica
    (CURRENT_DATE, (SELECT id FROM locations WHERE slug = 'santa_monica'), CURRENT_DATE + INTERVAL '6:55', CURRENT_DATE + INTERVAL '18:28', CURRENT_DATE + INTERVAL '6:25', CURRENT_DATE + INTERVAL '6:55', CURRENT_DATE + INTERVAL '17:58', CURRENT_DATE + INTERVAL '18:28'),
    
    -- Santa Barbara
    (CURRENT_DATE, (SELECT id FROM locations WHERE slug = 'santa_barbara'), CURRENT_DATE + INTERVAL '7:05', CURRENT_DATE + INTERVAL '18:38', CURRENT_DATE + INTERVAL '6:35', CURRENT_DATE + INTERVAL '7:05', CURRENT_DATE + INTERVAL '18:08', CURRENT_DATE + INTERVAL '18:38'),
    
    -- Morro Bay
    (CURRENT_DATE, (SELECT id FROM locations WHERE slug = 'morro_bay'), CURRENT_DATE + INTERVAL '7:15', CURRENT_DATE + INTERVAL '18:45', CURRENT_DATE + INTERVAL '6:45', CURRENT_DATE + INTERVAL '7:15', CURRENT_DATE + INTERVAL '18:15', CURRENT_DATE + INTERVAL '18:45'),
    
    -- Shaws Cove
    (CURRENT_DATE, (SELECT id FROM locations WHERE slug = 'shaws_cove'), CURRENT_DATE + INTERVAL '6:42', CURRENT_DATE + INTERVAL '18:15', CURRENT_DATE + INTERVAL '6:12', CURRENT_DATE + INTERVAL '6:42', CURRENT_DATE + INTERVAL '17:45', CURRENT_DATE + INTERVAL '18:15'),
    
    -- Zuma Beach
    (CURRENT_DATE, (SELECT id FROM locations WHERE slug = 'zuma_beach'), CURRENT_DATE + INTERVAL '6:56', CURRENT_DATE + INTERVAL '18:29', CURRENT_DATE + INTERVAL '6:26', CURRENT_DATE + INTERVAL '6:56', CURRENT_DATE + INTERVAL '17:59', CURRENT_DATE + INTERVAL '18:29')
ON CONFLICT (date, location_id) DO NOTHING;
