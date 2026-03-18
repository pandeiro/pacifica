"""Tests for Playwright-based scrapers (Harbor Breeze, Dana Wharf, Island Packers)."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "scraper"))

from harbor_breeze import HarborBreezeScraper
from dana_wharf import DanaWharfScraper, parse_sightings_text
from island_packers import IslandPackersScraper, parse_count


class TestHarborBreezeScraper:
    """Test suite for Harbor Breeze Scraper."""

    def test_scraper_initialization(self):
        """Test that the scraper initializes correctly."""
        scraper = HarborBreezeScraper()
        assert scraper.name == "harbor_breeze"
        assert scraper.location_slug == "long_beach"

    def test_schedule_defined(self):
        """Test that schedule is defined for scheduler discovery."""
        scraper = HarborBreezeScraper()
        assert hasattr(scraper, "schedule")
        assert scraper.schedule == "15 6 * * *"

    def test_url(self):
        """Test that URL is correct."""
        scraper = HarborBreezeScraper()
        assert scraper.url == "https://www.harbor-breeze.com/whale-watching-reports/"


class TestDanaWharfScraper:
    """Test suite for Dana Wharf Scraper."""

    def test_scraper_initialization(self):
        """Test that the scraper initializes correctly."""
        scraper = DanaWharfScraper()
        assert scraper.name == "dana_wharf"
        assert scraper.location_slug == "dana_point"

    def test_schedule_defined(self):
        """Test that schedule is defined for scheduler discovery."""
        scraper = DanaWharfScraper()
        assert hasattr(scraper, "schedule")
        assert scraper.schedule == "30 6 * * *"

    def test_csv_url(self):
        """Test that CSV URL is correct."""
        scraper = DanaWharfScraper()
        assert "docs.google.com/spreadsheets" in scraper.url
        assert "output=csv" in scraper.url

    def test_location_slug_exists(self):
        """Test that location slug maps to a known location."""
        scraper = DanaWharfScraper()
        assert scraper.location_slug == "dana_point"

    def test_parse_sightings_with_counts(self):
        """Test parsing sightings with counts."""
        text = "3 Fin whales, 10 gray whales, 1 mola mola"
        result = parse_sightings_text(text)
        assert (3, "Fin Whale") in result
        assert (10, "Gray Whale") in result
        assert (1, "Mola Mola") in result

    def test_parse_sightings_singular(self):
        """Test parsing sightings without counts (singular)."""
        text = "Common Dolphins, Bottlenose Dolphin"
        result = parse_sightings_text(text)
        assert (None, "Common Dolphin") in result
        assert (None, "Bottlenose Dolphin") in result

    def test_parse_sightings_mixed(self):
        """Test parsing mixed singular and counted sightings."""
        text = "2 Gray Whales, Common Dolphin"
        result = parse_sightings_text(text)
        assert (2, "Gray Whale") in result
        assert (None, "Common Dolphin") in result

    def test_parse_sightings_variations(self):
        """Test parsing with species name variations."""
        text = "Pacific White Sided Dolphins, Risso's Dolphins"
        result = parse_sightings_text(text)
        assert len(result) == 2


class TestIslandPackersScraper:
    """Test suite for Island Packers Scraper."""

    def test_scraper_initialization(self):
        """Test that the scraper initializes correctly."""
        scraper = IslandPackersScraper()
        assert scraper.name == "island_packers"
        assert scraper.location_slug == "ventura"

    def test_schedule_defined(self):
        """Test that schedule is defined for scheduler discovery."""
        scraper = IslandPackersScraper()
        assert hasattr(scraper, "schedule")
        assert scraper.schedule == "45 6 * * *"

    def test_csv_url(self):
        """Test that CSV URL is correct."""
        scraper = IslandPackersScraper()
        assert "docs.google.com/spreadsheets" in scraper.url

    def test_location_slug_exists(self):
        """Test that location slug maps to a known location."""
        scraper = IslandPackersScraper()
        assert scraper.location_slug == "ventura"

    def test_parse_count_valid(self):
        """Test parsing valid count values."""
        assert parse_count("5") == 5
        assert parse_count("10") == 10
        assert parse_count("1,650") == 1650
        assert parse_count("3,050") == 3050

    def test_parse_count_invalid(self):
        """Test parsing invalid count values."""
        assert parse_count("") is None
        assert parse_count("  ") is None
        assert parse_count("N/A") is None
        assert parse_count("0") is None

    def test_species_columns_mapping(self):
        """Test that species columns are mapped correctly."""
        from island_packers import SPECIES_COLUMNS

        assert "Humpback Whales" in SPECIES_COLUMNS
        assert SPECIES_COLUMNS["Humpback Whales"] == "Humpback Whale"
        assert SPECIES_COLUMNS["Gray Whales"] == "Gray Whale"
        assert SPECIES_COLUMNS["Common Dolphins"] == "Common Dolphin"


class TestPlaywrightDependency:
    """Test that Playwright is properly configured."""

    def test_playwright_import(self):
        """Test that Playwright can be imported."""
        try:
            from playwright.async_api import async_playwright

            assert async_playwright is not None
        except ImportError:
            pytest.skip("Playwright not installed")


class TestScheduleFormat:
    """Test that all scraper schedules follow cron format."""

    def test_harbor_breeze_cron_format(self):
        """Test Harbor Breeze schedule is valid cron."""
        parts = HarborBreezeScraper.schedule.split()
        assert len(parts) == 5
        assert parts[0] == "15"
        assert parts[1] == "6"

    def test_dana_wharf_cron_format(self):
        """Test Dana Wharf schedule is valid cron."""
        parts = DanaWharfScraper.schedule.split()
        assert len(parts) == 5
        assert parts[0] == "30"
        assert parts[1] == "6"

    def test_island_packers_cron_format(self):
        """Test Island Packers schedule is valid cron."""
        parts = IslandPackersScraper.schedule.split()
        assert len(parts) == 5
        assert parts[0] == "45"
        assert parts[1] == "6"
