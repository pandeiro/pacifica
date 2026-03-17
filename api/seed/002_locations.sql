-- 002_locations.sql
-- Additional coastal locations for expanded coverage
-- Extends 001_locations.sql with more Southern California stations

INSERT INTO locations (name, slug, lat, lng, location_type, region, noaa_station_id, coastline_bearing, description) VALUES
    -- San Diego
    ('San Diego', 'san_diego', 32.7156, -117.1767, 'harbor', 'south_coast', '9410170', NULL, 'San Diego Bay at Broadway Pier, southern terminus of Pacifica coverage'),
    ('Imperial Beach', 'imperial_beach', 32.5783, -117.1350, 'beach', 'south_coast', '9410120', 190.0, 'Southernmost beach on the California coast, popular for surfing and birdwatching'),
    
    -- Orange County
    ('Newport Beach', 'newport_beach', 33.6000, -117.9000, 'harbor', 'south_coast', '9410583', 180.0, 'Historic pier and harbor in central Orange County, prime surf spot'),
    
    -- Los Angeles
    ('Long Beach', 'long_beach', 33.7517, -118.2270, 'harbor', 'la_coast', '9410680', 180.0, 'Major port and harbor at Terminal Island, busy shipping channel'),
    ('Redondo Beach', 'redondo_beach', 33.8467, -118.3980, 'harbor', 'la_coast', '9410738', 225.0, 'King Harbor with marina and popular beach, good for diving and kayaking'),
    ('El Segundo', 'el_segundo', 33.9083, -118.4330, 'beach', 'la_coast', '9410777', 250.0, 'Beach and pier near LAX, consistent surf break'),
    
    -- Ventura
    ('Ventura', 'ventura', 34.2667, -119.2830, 'harbor', 'ventura', '9411189', 200.0, 'Harbor with access to Channel Islands, popular fishing and diving launch'),
    ('Port Hueneme', 'port_hueneme', 34.1483, -119.2030, 'harbor', 'ventura', '9411065', 190.0, 'Deep water port and naval base, good beach access'),
    
    -- Channel Islands
    ('Avalon, Catalina Island', 'avalon_catalina', 33.3450, -118.3250, 'harbor', 'channel_islands', '9410079', NULL, 'Main town on Santa Catalina Island, popular snorkeling and diving destination'),
    ('Prisoners Harbor, Santa Cruz Island', 'prisoners_harbor', 34.0200, -119.6830, 'harbor', 'channel_islands', '9410971', NULL, 'Remote harbor on Santa Cruz Island, excellent kayaking and hiking access'),
    ('Bechers Bay, Santa Rosa Island', 'bechers_bay', 34.0083, -120.0470, 'harbor', 'channel_islands', '9410962', NULL, 'Sheltered anchorage on Santa Rosa Island, pristine diving and snorkeling'),
    ('San Nicolas Island', 'san_nicolas_island', 33.2667, -119.4970, 'island', 'channel_islands', '9410068', NULL, 'Remote Navy-owned island, known for epic surf breaks and wildlife'),
    ('San Clemente Island', 'san_clemente_island', 33.0050, -118.5570, 'island', 'channel_islands', '9410032', NULL, 'Navy-owned island, legendary surf breaks like Trestles nearby'),
    
    -- Central Coast Extended
    ('San Simeon', 'san_simeon', 35.6417, -121.1880, 'harbor', 'central_coast', '9412553', NULL, 'Northern reach of Pacifica coverage, Hearst Castle nearby, elephant seal rookery'),
    ('Point Arguello', 'point_arguello', 34.5833, -120.6500, 'beach', 'central_coast', NULL, 270.0, 'Exposed headland with famous offshore kelp beds and rugged coastline')
ON CONFLICT (slug) DO NOTHING;
