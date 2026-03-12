# Technical Reference: Tides & Sun Slice

## 1. NOAA Tides Scraper (Card 07)
- **Source**: NOAA CO-OPS API.
- **Data**: Predictions (`interval=hilo`) for High/Low tide events.
- **Stations**: Dana Point, La Jolla, Santa Monica, Santa Barbara, Morro Bay.
- **Schedule**: Daily at 2 AM.
- **Storage**: `tides` hypertable.

## 2. Sun Events Scraper (Card 10)
- **Source**: `sunrise-sunset.org` API.
- **Data**: Sunrise, Sunset, Civil Twilight (used for Golden Hour).
- **Schedule**: Daily at 2:30 AM.
- **Storage**: `sun_events` table.

## 3. Tides API (Card 08)
- **Endpoint**: `GET /api/tides?station_id={id}&hours=48`.
- **Interpolation**: Calculates current water level linearly between the surrounding high/low events.
- **WebSocket**: Broadcasts `conditions.upserted` with `scraper: "noaa_tides"`.

## 4. Tides Frontend Tile (Card 09)
- **Visualization**: D3.js smooth curve through the 48-hour event window.
- **Components**:
    - `TidesCurve`: The SVG visualization with a pulsing current-position dot.
    - `NextTides`: Text display of upcoming High/Low events.
    - `SunEvents`: Solar events display.
- **Reactivity**: Re-fetches REST data upon receiving the relevant WebSocket update.
