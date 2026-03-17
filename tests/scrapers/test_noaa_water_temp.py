"""Tests for the NOAA Water Temperature Scraper."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
import sys
import os

# Add the scraper directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "scraper"))

from noaa_water_temp import NOAAWaterTempScraper


class TestNOAAWaterTempScraper:
    """Test suite for the NOAA Water Temperature Scraper."""

    def test_scraper_initialization(self):
        """Test that the scraper initializes correctly."""
        scraper = NOAAWaterTempScraper()
        assert scraper.name == "noaa_water_temp"
        assert scraper.schedule == "0 */6 * * *"

    @pytest.mark.asyncio
    async def test_calculate_hourly_averages(self):
        """Test calculation of hourly averages from readings."""
        scraper = NOAAWaterTempScraper()

        # Sample NOAA water temp readings (6-minute intervals)
        sample_readings = [
            {"t": "2026-03-16 12:00", "v": "62.4", "f": "0,0,0"},
            {"t": "2026-03-16 12:06", "v": "62.6", "f": "0,0,0"},
            {"t": "2026-03-16 12:12", "v": "62.6", "f": "0,0,0"},
            {"t": "2026-03-16 12:18", "v": "62.8", "f": "0,0,0"},
            {"t": "2026-03-16 12:24", "v": "62.8", "f": "0,0,0"},
            {"t": "2026-03-16 12:30", "v": "63.0", "f": "0,0,0"},
            {"t": "2026-03-16 12:36", "v": "63.0", "f": "0,0,0"},
            {"t": "2026-03-16 12:42", "v": "62.8", "f": "0,0,0"},
            {"t": "2026-03-16 12:48", "v": "62.8", "f": "0,0,0"},
            {"t": "2026-03-16 12:54", "v": "62.8", "f": "0,0,0"},
            {"t": "2026-03-16 13:00", "v": "63.0", "f": "0,0,0"},
        ]

        # Calculate hourly averages
        records = scraper._calculate_hourly_averages(1, "9410840", sample_readings)

        # Should get 2 hourly records (12:00 and 13:00)
        assert len(records) == 2

        # Check 12:00 hour average (10 readings)
        hour_12 = records[0]
        assert hour_12["location_id"] == 1
        assert hour_12["condition_type"] == "water_temp"
        assert hour_12["unit"] == "fahrenheit"
        assert hour_12["source"] == "noaa_9410840"
        # Average of [62.4, 62.6, 62.6, 62.8, 62.8, 63.0, 63.0, 62.8, 62.8, 62.8] = 62.76
        assert hour_12["value"] == 62.76

        # Check 13:00 hour average (1 reading)
        hour_13 = records[1]
        assert hour_13["value"] == 63.0

    @pytest.mark.asyncio
    async def test_calculate_hourly_averages_skips_empty(self):
        """Test that empty or invalid values are skipped."""
        scraper = NOAAWaterTempScraper()

        # Sample with empty values (as sometimes returned by NOAA)
        sample_readings = [
            {"t": "2026-03-16 12:00", "v": "62.4", "f": "0,0,0"},
            {"t": "2026-03-16 12:06", "v": "", "f": "1,1,1"},  # Empty value
            {"t": "2026-03-16 12:12", "v": "62.6", "f": "0,0,0"},
        ]

        records = scraper._calculate_hourly_averages(1, "9410840", sample_readings)

        assert len(records) == 1
        # Average of [62.4, 62.6] = 62.5
        assert records[0]["value"] == 62.5

    @pytest.mark.asyncio
    async def test_scrape_method_structure(self):
        """Test that the scrape method has the expected structure."""
        scraper = NOAAWaterTempScraper()

        # Mock the _fetch_water_temp method to avoid actual HTTP calls
        with patch.object(scraper, "_fetch_water_temp", AsyncMock(return_value=[])):
            result = await scraper.scrape()

            # Should return a list (even if empty)
            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_fetch_water_temp_handles_no_data(self):
        """Test handling of stations without water temp sensors."""
        scraper = NOAAWaterTempScraper()

        # Mock the HTTP client to return an error response
        mock_response = AsyncMock()
        mock_response.json.return_value = {"error": {"message": "No data was found"}}
        mock_response.raise_for_status = AsyncMock()

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            with patch("httpx.AsyncClient.__aenter__", return_value=mock_response):
                with patch("httpx.AsyncClient.__aexit__", return_value=False):
                    readings = await scraper._fetch_water_temp(
                        "9410660", datetime.now().date()
                    )
                    assert readings == []
