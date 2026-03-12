# Card 03 — Activity Score Formulas

## Goal
Define the exact scoring formulas for all five activity types. Scores are written to the `activity_scores` hypertable after each relevant scraper run. This card specifies the algorithm an agent can implement directly — no design decisions left open.

---

## Deliverables

1. `api/scoring.py` — scoring functions for all five activities
2. `api/scoring_triggers.py` — logic that decides which scores to recalculate after a given scraper run
3. Database migration — any indexes needed on `activity_scores`
4. Unit tests for every scoring function, covering boundary conditions

---

## General Conventions

**Score range**: 0–100 (integer)

**Score → label mapping** (used in UI and `summary_text`):
| Score | Label | Color |
|-------|-------|-------|
| 0–24 | Poor | Red |
| 25–44 | Fair | Orange |
| 45–64 | Good | Yellow |
| 65–84 | Great | Green |
| 85–100 | Epic | Teal |

**Sub-score pattern**: Each factor produces a sub-score 0–100, then factors are combined as a weighted sum. Weights sum to 1.0.

**Data freshness**: If a required input hasn't been updated in more than `2 × scraper_interval`, treat it as missing. Missing required factors (visibility for snorkeling, tide height for tidepooling) result in score = `null` — do not write a row. Missing optional factors use their neutral value (defined per activity below).

**Score recalculation**: Triggered after any scraper run that produced new records relevant to that activity. Multiple locations may be scored in a single pass. Write one row per `(location_id, activity_type)` per recalculation.

---

## Helper: Linear Interpolation

All factor sub-scores use piecewise linear interpolation between defined breakpoints:

```python
def interpolate(value: float, breakpoints: list[tuple[float, float]]) -> float:
    """
    breakpoints: list of (input_value, output_score) pairs, sorted ascending by input.
    Clamps to [0, 100].
    """
    if value <= breakpoints[0][0]:
        return breakpoints[0][1]
    if value >= breakpoints[-1][0]:
        return breakpoints[-1][1]
    for i in range(len(breakpoints) - 1):
        x0, y0 = breakpoints[i]
        x1, y1 = breakpoints[i + 1]
        if x0 <= value <= x1:
            t = (value - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    return 0.0
```

---

## Activity 1: Snorkeling

**Weights**: visibility 0.40 · swell 0.25 · marine life 0.20 · water temp 0.15 · (wind: see note)

Wind is folded into swell weight — high wind that's not yet producing swell is captured by the swell sub-score being low, and standalone wind rarely ruins a snorkel if swell is calm. Wind speed does not get its own factor slot.

### Visibility sub-score
Visibility is reported as a range (e.g. "15-30ft"). Use the **lower bound** as the input value — conservative scoring.

| Visibility lower bound (ft) | Sub-score |
|---|---|
| 0 | 0 |
| 5 | 10 |
| 10 | 45 |
| 15 | 70 |
| 20 | 88 |
| 30+ | 100 |

Visibility is **required**. If missing, score = `null`.

### Swell sub-score
Use swell height (ft) as primary input. If swell period is available, apply a modifier: period ≥ 14s (long-period ground swell) adds a 10-point penalty on top of height score — it creates surge even at modest heights.

| Swell height (ft) | Base sub-score |
|---|---|
| 0 | 100 |
| 1 | 95 |
| 2 | 80 |
| 3 | 55 |
| 4 | 25 |
| 5+ | 0 |

Long-period penalty: `if period >= 14: sub_score = max(0, sub_score - 10)`

### Marine life sub-score
Based on sightings at or near the location within the last **72 hours**. "Near" = same region.

```python
def marine_life_subscores(sightings: list[Sighting]) -> float:
    if not sightings:
        return 50  # neutral — absence of reports ≠ absence of life

    # Species point values
    SPECIES_POINTS = {
        "Orca":              40,
        "Blue whale":        35,
        "Humpback whale":    30,
        "Gray whale":        25,
        "Fin whale":         25,
        "Mola mola":         25,
        "Great white shark": 20,  # exciting but spooks some people — modest bonus
        "Leopard shark":     20,
        "Horn shark":        18,
        "Garibaldi":         10,
        "Sea otter":         20,
        # default for any unlisted species:
        "_default":           8,
    }

    total = sum(SPECIES_POINTS.get(s.species, SPECIES_POINTS["_default"]) for s in sightings)
    return min(100, total)  # cap at 100
```

Missing (no recent data): use 50 (neutral).

### Water temp sub-score

| Temp (°F) | Sub-score |
|---|---|
| 55 | 0 |
| 58 | 20 |
| 63 | 55 |
| 68 | 85 |
| 72+ | 100 |

Missing: use 50 (neutral).

### Final snorkeling score
```python
score = (
    visibility_sub  * 0.40 +
    swell_sub       * 0.25 +
    marine_life_sub * 0.20 +
    water_temp_sub  * 0.15
)
return round(score)
```

---

## Activity 2: Whale Watching

**Weights**: sighting frequency 0.45 · species quality 0.30 · season alignment 0.15 · sea conditions 0.10

### Sighting frequency sub-score
Count distinct sighting events (not individual animals) within **48 hours**, within the whale watching departure region (Dana Point, Long Beach/San Pedro, Ventura).

| Sighting events (48hr) | Sub-score |
|---|---|
| 0 | 5 |
| 1 | 30 |
| 2 | 55 |
| 3 | 70 |
| 4 | 82 |
| 5 | 90 |
| 7+ | 100 |

Zero sightings scores 5, not 0 — absence of recent reports doesn't mean nothing is out there.

### Species quality sub-score
Take the **single best species** sighted in the last 48 hours:

| Best species sighted | Sub-score |
|---|---|
| Orca | 100 |
| Blue whale | 90 |
| Humpback whale | 75 |
| Fin whale | 65 |
| Gray whale | 55 |
| Minke whale | 50 |
| Common dolphin | 30 |
| Bottlenose dolphin | 30 |
| No sightings | 10 |

### Season alignment sub-score
Based on current month and known migration/presence calendars. This is a prior — what's the baseline expectation for this time of year regardless of recent sightings?

| Month | Primary species in season | Sub-score |
|---|---|---|
| Jan | Gray whale (southbound) | 65 |
| Feb | Gray whale (southbound + turning) | 70 |
| Mar | Gray whale (northbound) | 70 |
| Apr | Gray/Humpback overlap | 75 |
| May | Humpback arriving | 70 |
| Jun | Blue + Humpback peak beginning | 80 |
| Jul | Blue + Humpback peak | 90 |
| Aug | Blue + Humpback peak | 90 |
| Sep | Blue + Humpback peak | 85 |
| Oct | Blue + Humpback, tapering | 75 |
| Nov | Mixed, slower | 55 |
| Dec | Gray whale early southbound | 60 |

### Sea conditions sub-score

| Combined swell (ft) + wind (mph) | Sub-score |
|---|---|
| Swell ≤2, wind ≤10 | 100 |
| Swell ≤3, wind ≤15 | 75 |
| Swell ≤4, wind ≤20 | 45 |
| Swell >4 or wind >20 | 15 |

Implement as: `conditions_sub = interpolate(max(swell_normalized, wind_normalized), ...)`
where `swell_normalized = swell_ft / 4` and `wind_normalized = wind_mph / 20`.

Missing conditions: use 75 (optimistic — conditions are usually fine in SoCal).

### Final whale watching score
```python
score = (
    frequency_sub * 0.45 +
    species_sub   * 0.30 +
    season_sub    * 0.15 +
    conditions_sub * 0.10
)
return round(score)
```

---

## Activity 3: Tidepooling

**Weights**: tide height 0.45 · time to next extreme low 0.30 · swell height 0.20 · recent sightings 0.05

### Tide height sub-score
Use the **current predicted tide height** in feet (MLLW). Lower is better.

| Tide height (ft) | Sub-score |
|---|---|
| -1.0 | 100 |
| 0.0 | 90 |
| 0.5 | 75 |
| 1.0 | 50 |
| 2.0 | 20 |
| 3.0+ | 0 |

Tide height is **required**. If missing, score = `null`.

### Time to next extreme low sub-score
How many hours until the next tide below 0.5ft?

| Hours to next extreme low | Sub-score |
|---|---|
| 0 (currently at low) | 100 |
| 1 | 90 |
| 2 | 75 |
| 4 | 45 |
| 6 | 20 |
| 12+ | 5 |

If next extreme low is more than 24 hours away: sub-score = 0.

### Swell sub-score (tidepooling)
Same breakpoints as snorkeling swell sub-score. Long-period penalty applies.

### Sightings sub-score
Recent sightings specifically tagged to tidepool location types within 7 days. Less time-sensitive than snorkeling.

| Recent tidepool sightings (7 days) | Sub-score |
|---|---|
| 0 | 50 |
| 1–2 | 65 |
| 3–5 | 80 |
| 6+ | 95 |

### Final tidepooling score
```python
score = (
    tide_height_sub  * 0.45 +
    time_to_low_sub  * 0.30 +
    swell_sub        * 0.20 +
    sightings_sub    * 0.05
)
return round(score)
```

---

## Activity 4: Body Surfing

**Weights**: waves 0.50 · water temp 0.25 · wind 0.15 · hazards 0.10

### Wave sub-score
Combines swell height and period. Body surfing wants punchy, mid-period waves — not too small, not too large.

| Swell height (ft) | Base sub-score |
|---|---|
| 0.5 | 10 |
| 1.0 | 35 |
| 1.5 | 60 |
| 2.0 | 80 |
| 2.5 | 90 |
| 3.0 | 85 |
| 4.0 | 65 |
| 5.0 | 35 |
| 6.0+ | 10 |

Period modifier (applied to base):
- Period 8–12s: +10 (punchy, fun)
- Period 6–8s: no change
- Period < 6s: −10 (too choppy)
- Period > 14s: −15 (too powerful, closes out)

`wave_sub = clamp(base + period_modifier, 0, 100)`

### Water temp sub-score (body surfing)
Body surfing without a wetsuit — temperature matters more than for snorkeling (where you're already suited up).

| Temp (°F) | Sub-score |
|---|---|
| 58 | 0 |
| 62 | 25 |
| 66 | 60 |
| 70 | 85 |
| 74+ | 100 |

### Wind sub-score
Onshore wind (blowing from ocean toward land) grooms waves for body surfing. Offshore is bad for body surfing (but good for board surfing). Cross-shore is neutral.

| Condition | Sub-score |
|---|---|
| Onshore, light (< 8mph) | 90 |
| Onshore, moderate (8–15mph) | 70 |
| Cross-shore, any speed | 55 |
| Calm / no wind | 60 |
| Offshore, any speed | 30 |
| Onshore, strong (>20mph) | 25 |

Wind direction from the conditions data — map compass bearing to onshore/offshore/cross based on the local coastline orientation of the selected location. Default assumption if direction unavailable: 55 (neutral).

### Hazard sub-score
Derived from scraper data and park closure flags. Binary check — any active hazard at the location halves the final score (applied after weighted sum, not as a factor).

Active hazards: great white shark advisory, rip current warning, beach closure, harmful algal bloom warning.

```python
if active_hazard_at_location:
    score = round(score * 0.5)
```

Missing hazard data: assume no hazard (optimistic).

### Final body surfing score
```python
raw_score = (
    wave_sub      * 0.50 +
    water_temp_sub * 0.25 +
    wind_sub       * 0.15 +
    100            * 0.10   # hazard starts at full marks, penalty applied after
)
score = round(raw_score)
if active_hazard:
    score = round(score * 0.5)
return score
```

---

## Activity 5: Scenic Drive

**Weights**: cloud cover 0.35 · air clarity 0.30 · golden hour proximity 0.25 · air temp 0.10

### Cloud cover sub-score
Clear skies are best. Some high clouds are fine. Overcast kills it.

| Cloud cover (%) | Sub-score |
|---|---|
| 0 | 100 |
| 10 | 95 |
| 30 | 75 |
| 50 | 50 |
| 70 | 25 |
| 90+ | 5 |

Cloud cover sourced from conditions data. Missing: use 60 (neutral — marine layer is common and not always reported).

### Air clarity sub-score
Proxy: use air temperature inversion indicators or visibility reports where available. In practice, use a simplified model:
- If `air_temp - water_temp > 8°F`: likely marine layer, clarity penalty → 40
- If recent wildfire smoke reports in metadata: → 15
- Otherwise: → 80 (SoCal default is clear)

This is a heuristic until a proper air quality source is added. Implement as a function that can be swapped out.

### Golden hour proximity sub-score
How close is the current time to golden hour (either morning or evening)?

| Minutes from nearest golden hour | Sub-score |
|---|---|
| 0 (inside golden hour) | 100 |
| 30 | 85 |
| 60 | 65 |
| 120 | 40 |
| 180 | 20 |
| 240+ | 10 |

Use `sun_events` table for golden hour start/end times. Always score against the **nearest** golden hour window (morning or evening).

### Air temp sub-score

| Air temp (°F) | Sub-score |
|---|---|
| 55 | 30 |
| 62 | 60 |
| 70 | 85 |
| 78 | 100 |
| 85 | 90 |
| 95+ | 55 |

### Final scenic drive score
```python
score = (
    cloud_cover_sub       * 0.35 +
    air_clarity_sub       * 0.30 +
    golden_hour_sub       * 0.25 +
    air_temp_sub          * 0.10
)
return round(score)
```

---

## Score Recalculation Triggers

After each scraper run, recalculate scores for affected activities and locations:

| Scraper | Recalculates |
|---|---|
| `noaa_water_temp` | snorkeling, body_surfing (all locations with new data) |
| `noaa_tides` | tidepooling (all locations) |
| `south_coast_divers` | snorkeling (Laguna locations) |
| `harbor_breeze`, `daveys_locker`, `dana_wharf`, `island_packers` | whale_watching (all departure regions) |
| `inaturalist` | snorkeling, tidepooling, whale_watching (location-specific) |
| `sunrise_sunset` | scenic_drive (all locations) |
| Any swell/wind conditions update | snorkeling, body_surfing, tidepooling, whale_watching |

Implement as a mapping in `scoring_triggers.py`:
```python
SCRAPER_SCORE_TRIGGERS: dict[str, list[str]] = {
    "noaa_water_temp":  ["snorkeling", "body_surfing"],
    "noaa_tides":       ["tidepooling"],
    "south_coast_divers": ["snorkeling"],
    ...
}
```

After recalculation, emit a `scores.updated` WebSocket message (via internal broadcast) with all newly calculated scores.

---

## `factors` JSONB Column

Every `activity_scores` row stores a breakdown of what drove the score, for display in the UI expandable and for debugging:

```json
{
  "inputs": {
    "visibility_ft_lower": 15,
    "swell_height_ft": 2.0,
    "swell_period_s": 10,
    "water_temp_f": 65,
    "marine_life_sightings": 3
  },
  "sub_scores": {
    "visibility": 70,
    "swell": 80,
    "marine_life": 68,
    "water_temp": 73
  },
  "weights": {
    "visibility": 0.40,
    "swell": 0.25,
    "marine_life": 0.20,
    "water_temp": 0.15
  },
  "missing_inputs": []
}
```

This is written by the scoring function automatically — no manual construction needed by callers.

---

## What's Out of Scope for This Card

- Sourcing air quality / cloud cover data (uses heuristic until a scraper is added)
- The `summary_text` LLM prompt (separate card — voice profile)
- Frontend score display (separate frontend card)

---

## Acceptance Criteria

- [ ] All five scoring functions return an integer 0–100
- [ ] Snorkeling with missing visibility returns `null`, not a score
- [ ] Tidepooling with missing tide height returns `null`, not a score
- [ ] Orca sighting produces whale watching score ≥ 85 regardless of season
- [ ] Body surfing with active hazard never scores above 50
- [ ] Snorkeling: vis=20ft, swell=1ft, 3 sightings, temp=67°F scores ≥ 80
- [ ] Tidepooling: tide=-0.5ft, 30min to low, swell=1ft scores ≥ 85
- [ ] Scenic drive: golden hour now, clear sky, 72°F scores ≥ 85
- [ ] Every score row written has a valid `factors` JSON column with `inputs`, `sub_scores`, `weights`
- [ ] `SCRAPER_SCORE_TRIGGERS` mapping tested — correct activities recalculated after each scraper type
- [ ] All breakpoint boundary values tested (at, just above, just below)
