"""Pydantic schemas for tides and sun events API."""

from datetime import datetime
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
    next_low: Optional[TideEvent] = None
    next_high: Optional[TideEvent] = None
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
