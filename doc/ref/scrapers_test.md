# Scraper Output Test

Generated: 2026-03-20 18:59  

This document shows the exact records each scraper would insert into the 
`sightings` table. `timestamp` is the scrape/ingest time (fixed for these 
tests); `sighting_date` is the date parsed from the source data.
A dummy `location_id=1` is used; `source_url` and `raw_text` omitted for brevity.

[1] ACS-LA — parse_date() unit tests
  [PASS] 2026-03-16   <- 'ACS/LA Gray Whale Census and Behavior Project Update, Pt. Vi'
  [PASS] 2026-03-16   <- 'Update March 16, 2026 - light winds. GRAY WHALES TODAY: Sout'
  [PASS] 2026-03-16   <- 'Posted 4 days ago — ACS/LA census report'
  [PASS] None         <- 'No date here. GRAY WHALES TODAY: Southbound: 5'

[1] ACS-LA — full record output

============================================================
  ACS-LA records
============================================================
  sighting_date : 2026-03-16
  timestamp    : 2026-03-20T14:00:00Z
  species      : Gray Whale (southbound)
  count       : 23
  source      : acs_la
  confidence  : high

  sighting_date : 2026-03-16
  timestamp    : 2026-03-20T14:00:00Z
  species      : Gray Whale (northbound)
  count       : 8
  source      : acs_la
  confidence  : high

  sighting_date : 2026-03-16
  timestamp    : 2026-03-20T14:00:00Z
  species      : Gray Whale (cow/calf)
  count       : 2
  source      : acs_la
  confidence  : high


[2] Dana Wharf — parse_sightings_text() unit tests
  [PASS] '3 Fin whales, 10 gray whales, 1 mola mola'
  [PASS] 'Common Dolphins'
  [PASS] '1 Orca, 50 Bottlenose Dolphin'

[2] Dana Wharf — full record output

============================================================
  Dana Wharf records
============================================================
  sighting_date : 2026-03-18
  timestamp    : 2026-03-20T14:00:00Z
  species      : Gray Whale
  count       : 10
  source      : dana_wharf
  confidence  : high

  sighting_date : 2026-03-18
  timestamp    : 2026-03-20T14:00:00Z
  species      : Fin Whale
  count       : 3
  source      : dana_wharf
  confidence  : high

  sighting_date : 2026-03-19
  timestamp    : 2026-03-20T14:00:00Z
  species      : Common Dolphin
  count       : 25
  source      : dana_wharf
  confidence  : high

  sighting_date : 2026-03-20
  timestamp    : 2026-03-20T14:00:00Z
  species      : Humpback Whale
  count       : 1
  source      : dana_wharf
  confidence  : high

  sighting_date : 2026-03-20
  timestamp    : 2026-03-20T14:00:00Z
  species      : Risso's Dolphin
  count       : 2
  source      : dana_wharf
  confidence  : high


[3] Harbor Breeze — _parse_date_from_text() unit tests
  [PASS] 2026-03-16   <- 'March 16, 2026 — 5 Humpback whales spotted'
  [PASS] 2026-03-16   <- '16 Mar 2026 — 2 Orca observed'
  [PASS] 2026-03-17   <- '03/17/2026 — 200 Common Dolphins'
  [PASS] None         <- 'No date here — just dolphins'

[3] Harbor Breeze — parse_sightings_from_text() unit tests
  [PASS] '500 Common Dolphins, 1 Humpback'
  [PASS] '2 Fin whales'
  [PASS] '1,000 Bottlenose Dolphin, 3 Gray whales'

[3] Harbor Breeze — full record output (date in heading, then sighting lines)

============================================================
  Harbor Breeze records
============================================================
  sighting_date : 2026-03-18
  timestamp    : 2026-03-20T14:00:00Z
  species      : Common Dolphin
  count       : 500
  source      : harbor_breeze
  confidence  : high

  sighting_date : 2026-03-18
  timestamp    : 2026-03-20T14:00:00Z
  species      : Gray Whale
  count       : 2
  source      : harbor_breeze
  confidence  : high

  sighting_date : 2026-03-19
  timestamp    : 2026-03-20T14:00:00Z
  species      : Humpback Whale
  count       : 1
  source      : harbor_breeze
  confidence  : high

  sighting_date : 2026-03-19
  timestamp    : 2026-03-20T14:00:00Z
  species      : Fin Whale
  count       : 3
  source      : harbor_breeze
  confidence  : high


[4] Davey's Locker — parse_species_list() unit tests
  [PASS] '53 Gray Whales, 103 Bottlenose Dolphin'
  [PASS] '1 Fin Whale, 1100 Common Dolphin, 1 Mola Mola'
  [PASS] 'No sightings today'

[4] Davey's Locker — full record output

============================================================
  Davey's Locker records
============================================================
  sighting_date : 2026-03-18
  timestamp    : 2026-03-20T14:00:00Z
  species      : Gray Whales
  count       : 53
  source      : daveyslocker
  confidence  : high

  sighting_date : 2026-03-18
  timestamp    : 2026-03-20T14:00:00Z
  species      : Bottlenose Dolphin
  count       : 103
  source      : daveyslocker
  confidence  : high

  sighting_date : 2026-03-18
  timestamp    : 2026-03-20T14:00:00Z
  species      : Common Dolphin
  count       : 625
  source      : daveyslocker
  confidence  : high

  sighting_date : 2026-03-19
  timestamp    : 2026-03-20T14:00:00Z
  species      : Gray Whales
  count       : 12
  source      : daveyslocker
  confidence  : high

  sighting_date : 2026-03-19
  timestamp    : 2026-03-20T14:00:00Z
  species      : Fin Whale
  count       : 1
  source      : daveyslocker
  confidence  : high

  sighting_date : 2026-03-19
  timestamp    : 2026-03-20T14:00:00Z
  species      : Common Dolphin
  count       : 1100
  source      : daveyslocker
  confidence  : high


[5] Island Packers — parse_count() unit tests
  [PASS] parse_count('15') = 15
  [PASS] parse_count('1,000') = 1000
  [PASS] parse_count('') = None
  [PASS] parse_count('abc') = None
  [PASS] parse_count('0') = None

[5] Island Packers — full record output

============================================================
  Island Packers records
============================================================
  sighting_date : 2026-03-03
  timestamp    : 2026-03-20T18:59:29Z
  species      : Humpback Whale
  count       : 5
  source      : island_packers
  confidence  : high

  sighting_date : 2026-03-03
  timestamp    : 2026-03-20T18:59:29Z
  species      : Common Dolphin
  count       : 200
  source      : island_packers
  confidence  : high

  sighting_date : 2026-03-04
  timestamp    : 2026-03-20T18:59:29Z
  species      : Blue Whale
  count       : 1
  source      : island_packers
  confidence  : high

  sighting_date : 2026-03-04
  timestamp    : 2026-03-20T18:59:29Z
  species      : Gray Whale
  count       : 3
  source      : island_packers
  confidence  : high

  sighting_date : 2026-03-05
  timestamp    : 2026-03-20T18:59:29Z
  species      : Humpback Whale
  count       : 12
  source      : island_packers
  confidence  : high

  sighting_date : 2026-03-05
  timestamp    : 2026-03-20T18:59:29Z
  species      : Common Dolphin
  count       : 50
  source      : island_packers
  confidence  : high


[6] iNaturalist — _parse_observation() unit tests
  [PASS] valid observation, research grade
  [PASS] no geojson → None
  [PASS] outside 30 mi radius → None

[6] iNaturalist — full aggregate record output (mock)

============================================================
  iNaturalist aggregate records
============================================================
  sighting_date : 2026-03-20
  timestamp    : 2026-03-20T18:59:29Z
  species      : Common Dolphin
  count       : 8
  source      : inaturalist
  confidence  : medium

  sighting_date : 2026-03-20
  timestamp    : 2026-03-20T18:59:29Z
  species      : Gray Whale
  count       : 2
  source      : inaturalist
  confidence  : high

