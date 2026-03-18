"""Tests for Playwright-based scrapers (Harbor Breeze, Dana Wharf, Island Packers)."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "scraper"))

from harbor_breeze import HarborBreezeScraper
from dana_wharf import DanaWharfScraper
from island_packers import IslandPackersScraper


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

    def test_extract_reports_basic(self):
        """Test extraction of trip report content."""
        scraper = HarborBreezeScraper()

        html = """
        <html><body>
        <article>
            <p>We saw 5 gray whales and 100 common dolphins today!</p>
        </article>
        </body></html>
        """
        reports = scraper._extract_reports(html)
        assert len(reports) >= 1
        assert any("whale" in r.lower() or "dolphin" in r.lower() for r in reports)

    def test_extract_reports_with_class_selectors(self):
        """Test extraction using class-based selectors."""
        scraper = HarborBreezeScraper()

        html = """
        <html><body>
        <div class="trip-report">
            Great day! Saw 3 blue whales and plenty of dolphins.
        </div>
        <div class="sighting">
            Morning trip: 2 humpback whales
        </div>
        </body></html>
        """
        reports = scraper._extract_reports(html)
        assert len(reports) >= 1

    def test_extract_reports_no_content(self):
        """Test handling of page with no reports."""
        scraper = HarborBreezeScraper()

        html = "<html><body><p>No whale reports here</p></body></html>"
        reports = scraper._extract_reports(html)
        assert reports == []

    def test_location_slug_exists(self):
        """Test that location slug maps to a known location."""
        scraper = HarborBreezeScraper()
        # 'long_beach' should exist in seed data
        assert scraper.location_slug == "long_beach"


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

    def test_url(self):
        """Test that URL is correct."""
        scraper = DanaWharfScraper()
        assert scraper.url == "https://danawharf.com/whale-watching/"

    def test_extract_log_section_basic(self):
        """Test extraction of log section from HTML."""
        scraper = DanaWharfScraper()

        html = """
        <html><body>
        <div id="log">
            Today we saw 2 gray whales and 50 common dolphins.
            Great visibility!
        </div>
        </body></html>
        """
        log = scraper._extract_log_section(html)
        assert "gray whale" in log.lower() or "dolphin" in log.lower()

    def test_extract_log_section_with_wildlife_keywords(self):
        """Test that wildlife keywords are detected."""
        scraper = DanaWharfScraper()

        html = """
        <html><body>
        <main>
            <p>Blue whale sighting today at 2pm.</p>
            <p>Also spotted some fin whales.</p>
        </main>
        </body></html>
        """
        log = scraper._extract_log_section(html)
        assert len(log) > 0

    def test_extract_log_section_empty(self):
        """Test handling of empty content."""
        scraper = DanaWharfScraper()

        html = "<html><body></body></html>"
        log = scraper._extract_log_section(html)
        assert log == ""

    def test_location_slug_exists(self):
        """Test that location slug maps to a known location."""
        scraper = DanaWharfScraper()
        # 'dana_point' should exist in seed data
        assert scraper.location_slug == "dana_point"


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

    def test_url(self):
        """Test that URL is correct."""
        scraper = IslandPackersScraper()
        assert (
            scraper.url
            == "https://islandpackers.com/information/marine-mammal-sightings/"
        )

    def test_extract_island_mention_anacapa(self):
        """Test extraction of Anacapa Island mention."""
        scraper = IslandPackersScraper()

        text = "We saw blue whales near Anacapa Island today."
        island = scraper._extract_island_mention(text)
        assert island == "Anacapa"

    def test_extract_island_mention_santa_cruz(self):
        """Test extraction of Santa Cruz Island mention."""
        scraper = IslandPackersScraper()

        text = "Great humpback sighting off Santa Cruz Island."
        island = scraper._extract_island_mention(text)
        assert island == "Santa Cruz"

    def test_extract_island_mention_none(self):
        """Test when no island is mentioned."""
        scraper = IslandPackersScraper()

        text = "We saw whales in the Santa Barbara Channel."
        island = scraper._extract_island_mention(text)
        assert island is None

    def test_extract_island_mention_case_insensitive(self):
        """Test island extraction is case insensitive."""
        scraper = IslandPackersScraper()

        text = "Dolphins spotted near santa rosa island."
        island = scraper._extract_island_mention(text)
        assert island == "Santa Rosa"

    def test_extract_sightings_text_basic(self):
        """Test extraction of sightings text from HTML."""
        scraper = IslandPackersScraper()

        html = """
        <html><body>
        <article>
            <p>Blue whales spotted near Santa Cruz Island</p>
            <p>Common dolphins seen throughout the channel</p>
        </article>
        </body></html>
        """
        sightings = scraper._extract_sightings_text(html)
        assert len(sightings) >= 1
        # Check that wildlife keywords are present
        all_text = " ".join([s["text"] for s in sightings])
        assert "whale" in all_text.lower() or "dolphin" in all_text.lower()

    def test_extract_sightings_text_with_island(self):
        """Test that island metadata is extracted."""
        scraper = IslandPackersScraper()

        html = """
        <html><body>
        <div class="sightings">
            Humpback whales feeding near Santa Cruz Island.
        </div>
        </body></html>
        """
        sightings = scraper._extract_sightings_text(html)
        assert len(sightings) >= 1
        assert sightings[0]["island"] == "Santa Cruz"

    def test_location_slug_exists(self):
        """Test that location slug maps to a known location."""
        scraper = IslandPackersScraper()
        # 'ventura' should exist in seed data
        assert scraper.location_slug == "ventura"


class TestPlaywrightDependency:
    """Test that Playwright is properly configured."""

    def test_playwright_import(self):
        """Test that Playwright can be imported."""
        try:
            from playwright.async_api import async_playwright

            assert async_playwright is not None
        except ImportError:
            pytest.skip("Playwright not installed")

    def test_browser_launch_capability(self):
        """Test that browser can be launched (requires Playwright install)."""
        pytest.skip("Browser launch test requires Playwright installation")


class TestScheduleFormat:
    """Test that all scraper schedules follow cron format."""

    def test_harbor_breeze_cron_format(self):
        """Test Harbor Breeze schedule is valid cron."""
        parts = HarborBreezeScraper.schedule.split()
        assert len(parts) == 5
        assert parts[0] == "15"  # minute
        assert parts[1] == "6"  # hour (6:15 AM)

    def test_dana_wharf_cron_format(self):
        """Test Dana Wharf schedule is valid cron."""
        parts = DanaWharfScraper.schedule.split()
        assert len(parts) == 5
        assert parts[0] == "30"  # minute
        assert parts[1] == "6"  # hour (6:30 AM)

    def test_island_packers_cron_format(self):
        """Test Island Packers schedule is valid cron."""
        parts = IslandPackersScraper.schedule.split()
        assert len(parts) == 5
        assert parts[0] == "45"  # minute
        assert parts[1] == "6"  # hour (6:45 AM)
