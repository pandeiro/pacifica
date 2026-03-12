# Technical Reference: Scoring Logic

## 1. General Principles
Scores range from **0 to 100**.
- **Piecewise Linear Interpolation**: All factor sub-scores are calculated by interpolating between defined breakpoints.
- **Weighted Average**: Factor scores are combined using specific weights.
- **Freshness Requirement**: If a required input is older than its expected interval, the final activity score is set to `null`.

## 2. Activity Formulas

### Snorkeling
- **Weights**: Visibility (0.40), Swell (0.25), Marine Life (0.20), Water Temp (0.15).
- **Required**: Visibility.

### Whale Watching
- **Weights**: Sighting Frequency (0.45), Species Quality (0.30), Season Alignment (0.15), Sea Conditions (0.10).

### Tidepooling
- **Weights**: Tide Height (0.45), Time to Next Low (0.30), Swell (0.20), Recent Sightings (0.05).
- **Required**: Tide Height.

### Body Surfing
- **Weights**: Waves (0.50), Water Temp (0.25), Wind (0.15), Hazards (0.10).
- **Modifier**: Active hazards (e.g., shark advisory) halving the final score.

### Scenic Drive
- **Weights**: Cloud Cover (0.35), Air Clarity (0.30), Golden Hour Proximity (0.25), Air Temp (0.10).

## 3. Triggers
Recalculation is triggered by the completion of relevant scrapers (e.g., `noaa_tides` triggers `tidepooling` score updates).
