"""Pydantic schemas for tides and sun events API."""

from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, Field


class TideEvent(BaseModel):
    """Single tide event (high or low tide)."""

    timestamp: datetime
    type: str = Field(..., pattern="^(high|low|predicted)$")
    height_ft: float

    class Config:
        from_attributes = True


class StationInfo(BaseModel):
    """Information about the data source station."""

    name: str
    station_id: str
    distance_miles: float
    direction: str

    class Config:
        from_attributes = True


class TidesResponse(BaseModel):
    """Response model for tides endpoint."""

    station_id: str
    location_name: str
    events: list[TideEvent]
    next_tide: Optional[TideEvent] = None
    next_tide_after: Optional[TideEvent] = None
    current_height_ft: Optional[float] = None
    data_through: datetime
    station_info: Optional[StationInfo] = None

    class Config:
        from_attributes = True


class SunEventsResponse(BaseModel):
    """Response model for sun events endpoint."""

    location_id: int
    location_name: str
    date: str
    sunrise: datetime
    sunset: datetime
    golden_hour_morning_start: datetime
    golden_hour_morning_end: datetime
    golden_hour_evening_start: datetime
    golden_hour_evening_end: datetime

    class Config:
        from_attributes = True


class WaterTemperatureReading(BaseModel):
    """Single water temperature reading."""

    timestamp: datetime
    temperature_f: float
    source: str
    source_url: Optional[str] = None

    class Config:
        from_attributes = True


class WaterTemperatureResponse(BaseModel):
    """Response model for water temperature endpoint."""

    location_id: int
    location_name: str
    current_temp_f: Optional[float] = None
    current_temp_c: Optional[float] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    last_updated: Optional[datetime] = None
    history: list[WaterTemperatureReading]
    hours_requested: int
    readings_count: int
    station_info: Optional[StationInfo] = None

    class Config:
        from_attributes = True


class VisibilityHistoryItem(BaseModel):
    """Single visibility reading for historical chart."""

    timestamp: datetime
    visibility_max: int

    class Config:
        from_attributes = True


class VisibilityResponse(BaseModel):
    """Response model for water visibility endpoint."""

    location_id: int
    location_name: str
    visibility_min: Optional[int] = None
    visibility_max: Optional[int] = None
    swell_min: Optional[int] = None
    swell_max: Optional[int] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    last_updated: Optional[datetime] = None
    history: list[VisibilityHistoryItem] = []

    class Config:
        from_attributes = True


class SightingRecord(BaseModel):
    """Single wildlife sighting record."""

    id: int
    timestamp: datetime
    sighting_date: Optional[date] = None
    species: str
    taxon_group: str
    count: Optional[int] = None
    location_id: Optional[int] = None
    location_name: Optional[str] = None
    source: str
    source_url: Optional[str] = None
    confidence: str
    raw_text: Optional[str] = None
    metadata: dict = Field(default_factory=dict)

    class Config:
        from_attributes = True


class SightingsResponse(BaseModel):
    """Response model for sightings endpoint."""

    sightings: list[SightingRecord]
    total: int
    days_requested: int

    class Config:
        from_attributes = True
