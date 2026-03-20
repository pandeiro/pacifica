"""Tests for the ACS-LA Gray Whale Census Scraper."""

import pytest
from datetime import datetime
from unittest.mock import patch
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "scraper"))

from acs_la import (
    ACSLAScraper,
    extract_structured_counts,
    is_gray_whale_season,
    parse_date,
)


class TestIsGrayWhaleSeason:
    """Test suite for season detection."""

    def test_december_is_season(self):
        """December is in gray whale season."""
        with patch("acs_la.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 12, 15)
            assert is_gray_whale_season() is True

    def test_january_is_season(self):
        """January is in gray whale season."""
        with patch("acs_la.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 1, 15)
            assert is_gray_whale_season() is True

    def test_may_is_season(self):
        """May is in gray whale season."""
        with patch("acs_la.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 5, 15)
            assert is_gray_whale_season() is True

    def test_june_not_season(self):
        """June is outside gray whale season."""
        with patch("acs_la.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 6, 15)
            assert is_gray_whale_season() is False

    def test_august_not_season(self):
        """August is outside gray whale season."""
        with patch("acs_la.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 8, 15)
            assert is_gray_whale_season() is False


class TestExtractStructuredCounts:
    """Test suite for structured count extraction."""

    def test_basic_counts(self):
        """Test basic count extraction."""
        text = """
        GRAY WHALES TODAY:
        Southbound: 12
        Northbound: 5
        Cow/calves south: 2
        Total: 17
        """
        result = extract_structured_counts(text)
        assert result["southbound"] == 12
        assert result["northbound"] == 5
        assert result["cow_calves_south"] == 2
        assert result["total"] == 17

    def test_case_insensitive(self):
        """Test case-insensitive matching."""
        text = """
        GRAY WHALES TODAY:
        SOUTHBOUND: 8
        NORTHBOUND: 3
        TOTAL: 11
        """
        result = extract_structured_counts(text)
        assert result["southbound"] == 8
        assert result["northbound"] == 3
        assert result["total"] == 11

    def test_whitespace_variations(self):
        """Test handling of whitespace variations."""
        text = """
        GRAY WHALES TODAY:
        Southbound:  15
        Northbound:7
        Total:  22
        """
        result = extract_structured_counts(text)
        assert result["southbound"] == 15
        assert result["northbound"] == 7
        assert result["total"] == 22

    def test_cow_calves_variations(self):
        """Test cow/calf count extraction."""
        text = """
        GRAY WHALES TODAY:
        Cow/calves south: 3
        """
        result = extract_structured_counts(text)
        assert result["cow_calves_south"] == 3

    def test_missing_counts(self):
        """Test when some counts are missing."""
        text = """
        GRAY WHALES TODAY:
        Southbound: 10
        Northbound: 5
        """
        result = extract_structured_counts(text)
        assert result["southbound"] == 10
        assert result["northbound"] == 5
        assert result["cow_calves_south"] == 0
        assert result["total"] == 0

    def test_empty_text(self):
        """Test empty text returns zeros."""
        result = extract_structured_counts("")
        assert result["southbound"] == 0
        assert result["northbound"] == 0
        assert result["cow_calves_south"] == 0
        assert result["total"] == 0

    def test_no_matching_pattern(self):
        """Test text without matching patterns."""
        text = "No whale census data available today."
        result = extract_structured_counts(text)
        assert result["southbound"] == 0
        assert result["northbound"] == 0

    def test_real_world_format(self):
        """Test parsing realistic census post format - only TODAY section, not TO DATE."""
        text = """
        GRAY WHALES TODAY:
        Southbound: 23
        Northbound: 8
        Cow/calves south: 2
        Total: 33

        GRAY WHALES TO DATE (since 1 Dec)
        Southbound: 847
        Northbound: 312
        """
        result = extract_structured_counts(text)
        assert result["southbound"] == 23
        assert result["northbound"] == 8
        assert result["cow_calves_south"] == 2
        assert result["total"] == 33


class TestACSLAScraper:
    """Test suite for ACS-LA Scraper."""

    def test_scraper_initialization(self):
        """Test that the scraper initializes correctly."""
        scraper = ACSLAScraper()
        assert scraper.name == "acs_la"
        assert scraper.location_slug == "point_vicente"

    def test_schedule_defined(self):
        """Test that schedule is defined for scheduler discovery."""
        scraper = ACSLAScraper()
        assert hasattr(scraper, "schedule")
        assert scraper.schedule == "0 9 * * *"

    def test_url(self):
        """Test that URL is correct."""
        scraper = ACSLAScraper()
        assert scraper.url == "https://acs-la.org/todays-whale-count/"

    def test_extract_facebook_posts_basic(self):
        """Test extraction of Facebook post content."""
        scraper = ACSLAScraper()

        html = """
        <html><body>
        <div class="cff-text">GRAY WHALES TODAY:
        Southbound: 12
        Northbound: 5</div>
        </body></html>
        """

        posts = scraper._extract_facebook_posts(html)
        assert len(posts) == 1
        assert "Southbound: 12" in posts[0]

    def test_extract_facebook_posts_multiple(self):
        """Test extraction of multiple posts."""
        scraper = ACSLAScraper()

        html = """
        <html><body>
        <div class="cff-text">First post</div>
        <div class="cff-text">Second post</div>
        </body></html>
        """

        posts = scraper._extract_facebook_posts(html)
        assert len(posts) == 2

    def test_extract_facebook_posts_empty(self):
        """Test handling of page with no posts."""
        scraper = ACSLAScraper()

        html = "<html><body><p>No posts here</p></body></html>"
        posts = scraper._extract_facebook_posts(html)
        assert posts == []

    @pytest.mark.asyncio
    async def test_scrape_outside_season(self):
        """Test that scraper skips when outside whale season."""
        scraper = ACSLAScraper()

        with patch("acs_la.is_gray_whale_season", return_value=False):
            result = await scraper.scrape()
            assert result == []

    @pytest.mark.asyncio
    async def test_scrape_method_structure(self):
        """Test that the scrape method has the expected structure."""
        scraper = ACSLAScraper()

        assert hasattr(scraper, "scrape")
        assert callable(scraper.scrape)


class TestCensusPostFormats:
    """Test handling of various real-world census post formats."""

    def test_format_with_narrative(self):
        """Test parsing post with narrative before counts."""
        text = """
        Beautiful day on the Point! Clear skies, light winds.

        GRAY WHALES TODAY:
        Southbound: 18
        Northbound: 3
        Cow/calves south: 1
        Total: 22

        Volunteers spotted several pods close to shore.
        """
        result = extract_structured_counts(text)
        assert result["southbound"] == 18
        assert result["northbound"] == 3
        assert result["cow_calves_south"] == 1
        assert result["total"] == 22

    def test_format_with_extra_whitespace(self):
        """Test parsing with extra whitespace and newlines."""
        text = """

        GRAY WHALES TODAY:

        Southbound:  25

        Northbound:  12


        Total:  37
        """
        result = extract_structured_counts(text)
        assert result["southbound"] == 25
        assert result["northbound"] == 12

    def test_format_with_colon_in_value(self):
        """Test that multiple colons don't break parsing."""
        text = """
        GRAY WHALES TODAY:
        Southbound: 15 (estimated: 12-18)
        """
        result = extract_structured_counts(text)
        assert result["southbound"] == 15

    def test_ignores_to_date_section(self):
        """Test that TO DATE cumulative section is ignored."""
        text = """
        GRAY WHALES TODAY:
        Southbound: 0
        Northbound: 0
        Total: 0

        GRAY WHALES TO DATE (since 1 Dec)
        Southbound: 847
        Northbound: 312
        Total: 1159
        """
        result = extract_structured_counts(text)
        assert result["southbound"] == 0
        assert result["northbound"] == 0
        assert result["total"] == 0


class TestParseDate:
    """Test suite for ACS-LA post date extraction."""

    def test_full_month_name(self):
        """'16 March 2026' should parse to 2026-03-16."""
        text = "ACS/LA Gray Whale Census, Pt. Vicente Interpretive Center, 16 March 2026 - heavy fog"
        result = parse_date(text)
        assert result is not None
        assert result.year == 2026
        assert result.month == 3
        assert result.day == 16

    def test_month_name_with_comma(self):
        """'March 16, 2026' should parse."""
        text = "GRAY WHALES TODAY: Some content. ACS/LA update March 16, 2026."
        result = parse_date(text)
        assert result is not None
        assert result.year == 2026
        assert result.month == 3
        assert result.day == 16

    def test_abbreviated_month(self):
        """'16 Mar 2026' should parse."""
        text = "Update: 16 Mar 2026 - light winds"
        result = parse_date(text)
        assert result is not None
        assert result.year == 2026
        assert result.month == 3
        assert result.day == 16

    def test_no_date_returns_none(self):
        """Text with no date patterns should return None."""
        result = parse_date("GRAY WHALES TODAY: Southbound: 5")
        assert result is None
