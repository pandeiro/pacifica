"""Tests for the NOAA Tides Scraper."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
import sys
import os

# Add the scraper directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "scraper"))

from noaa_tides import NOAATidesScraper, STATIONS


class TestNOAATidesScraper:
    """Test suite for the NOAA Tides Scraper."""

    def test_scraper_initialization(self):
        """Test that the scraper initializes correctly."""
        scraper = NOAATidesScraper()
        assert scraper.name == "noaa_tides"

    def test_stations_defined(self):
        """Test that station mappings are defined."""
        assert len(STATIONS) == 5
        assert "9410660" in STATIONS  # Dana Point
        assert "9410230" in STATIONS  # La Jolla
        assert "9410840" in STATIONS  # Santa Monica
        assert "9411340" in STATIONS  # Santa Barbara
        assert "9412110" in STATIONS  # Morro Bay

    @pytest.mark.asyncio
    async def test_process_predictions(self):
        """Test processing of NOAA prediction data."""
        scraper = NOAATidesScraper()

        # Sample NOAA predictions data
        sample_predictions = [
            {"t": "2026-03-16 06:23", "v": "5.123", "type": "H"},
            {"t": "2026-03-16 12:45", "v": "-0.234", "type": "L"},
        ]

        # Process the predictions
        records = scraper._process_predictions("9410660", sample_predictions)

        # Check that we get the expected number of records
        assert len(records) == 2

        # Check the first record (high tide)
        high_tide = records[0]
        assert high_tide["station_id"] == "9410660"
        assert high_tide["type"] == "high"
        assert high_tide["height_ft"] == 5.123
        assert high_tide["source"] == "noaa_predictions"

        # Check the second record (low tide)
        low_tide = records[1]
        assert low_tide["station_id"] == "9410660"
        assert low_tide["type"] == "low"
        assert low_tide["height_ft"] == -0.234
        assert low_tide["source"] == "noaa_predictions"

    @pytest.mark.asyncio
    async def test_scrape_method_structure(self):
        """Test that the scrape method has the expected structure."""
        scraper = NOAATidesScraper()

        # Mock the _fetch_predictions method to avoid actual HTTP calls
        with patch.object(scraper, "_fetch_predictions", AsyncMock(return_value=[])):
            result = await scraper.scrape()

            # Should return a list (even if empty)
            assert isinstance(result, list)
