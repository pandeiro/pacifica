"""Tests for the iNaturalist Scraper — daily aggregate design."""

import pytest
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "scraper"))

from inaturalist import INatScraper, INAT_TAXA, SOCAL_BBOX


class TestINatScraper:
    """Test suite for the iNaturalist Scraper."""

    def test_scraper_initialization(self):
        """Test that the scraper initializes correctly."""
        scraper = INatScraper()
        assert scraper.name == "inaturalist"

    def test_schedule_is_daily(self):
        """Test that schedule runs once per day (not every 30 min)."""
        scraper = INatScraper()
        assert hasattr(scraper, "schedule")
        assert scraper.schedule == "0 7 * * *"

    def test_prior_day(self):
        """Test _prior_day returns yesterday's date."""
        scraper = INatScraper()
        with patch("inaturalist.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 19, tzinfo=timezone.utc)
            mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            pd = scraper._prior_day()
        assert pd == date(2026, 3, 18)

    def test_taxa_defined(self):
        """Test that taxa mappings are defined with correct IDs."""
        assert len(INAT_TAXA) == 14
        taxon_ids = [tid for tid, _ in INAT_TAXA]
        assert 152871 in taxon_ids  # Cetacea
        assert 372843 in taxon_ids  # Phocoidea
        assert 41859 in taxon_ids  # Enhydra (sea otters)
        assert 47668 in taxon_ids  # Asteroidea
        assert 47459 in taxon_ids  # Cephalopoda
        assert 47178 in taxon_ids  # Actinopterygii
        assert 47187 in taxon_ids  # Malacostraca (crabs, lobsters)
        assert 116999 in taxon_ids  # Osprey
        assert 5305 in taxon_ids  # Bald Eagle
        assert 4647 in taxon_ids  # Peregrine Falcon

    def test_bbox_defined(self):
        """Test that bounding box coordinates are defined."""
        assert "swlat" in SOCAL_BBOX
        assert "swlng" in SOCAL_BBOX
        assert "nelat" in SOCAL_BBOX
        assert "nelng" in SOCAL_BBOX
        assert SOCAL_BBOX["swlat"] < SOCAL_BBOX["nelat"]
        assert SOCAL_BBOX["swlng"] < SOCAL_BBOX["nelng"]

    @pytest.mark.asyncio
    async def test_parse_observation_with_location(self):
        """Test parsing an observation with valid location returns count + species."""
        scraper = INatScraper()

        mock_obs = {
            "id": 12345,
            "geojson": {"coordinates": [-118.5, 34.0]},
            "observed_on": "2026-03-15",
            "time_observed_at": "2026-03-15T14:30:00Z",
            "taxon": {
                "preferred_common_name": "Common Dolphin",
                "name": "Delphinus delphis",
            },
            "quality_grade": "research",
            "count": 5,
        }

        mock_session = MagicMock()

        with patch(
            "inaturalist.find_nearest_location",
            AsyncMock(return_value=(1, None)),
        ):
            result = await scraper._parse_observation(mock_obs, mock_session)

        assert result is not None
        assert result["species"] == "Common Dolphin"
        assert result["location_id"] == 1
        assert result["confidence"] == "high"
        assert result["count"] == 5
        assert result["obs_id"] == 12345
        assert result["source"] == "inaturalist"
        assert result["source_url"] == "https://www.inaturalist.org/observations/12345"

    @pytest.mark.asyncio
    async def test_parse_observation_skips_outside_radius(self):
        """Test that observations outside 30mi radius return None."""
        scraper = INatScraper()

        mock_obs = {
            "id": 12348,
            "geojson": {"coordinates": [-150.0, 40.0]},  # Far outside SoCal
            "observed_on": "2026-03-15",
            "taxon": {"preferred_common_name": "Gray Whale"},
            "quality_grade": "research",
        }

        mock_session = MagicMock()

        with patch(
            "inaturalist.find_nearest_location",
            AsyncMock(return_value=(None, None)),
        ):
            result = await scraper._parse_observation(mock_obs, mock_session)

        assert result is None

    @pytest.mark.asyncio
    async def test_parse_observation_no_geojson(self):
        """Test that observations without geojson return None."""
        scraper = INatScraper()

        mock_obs = {"id": 12347, "observed_on": "2026-03-15"}

        mock_session = MagicMock()
        result = await scraper._parse_observation(mock_obs, mock_session)

        assert result is None

    @pytest.mark.asyncio
    async def test_aggregate_groups_by_location_and_species(self):
        """Test that _aggregate correctly groups observations."""
        scraper = INatScraper()

        observations = [
            {
                "id": 1,
                "geojson": {"coordinates": [-118.5, 34.0]},
                "observed_on": "2026-03-15",
                "taxon": {"preferred_common_name": "Common Dolphin"},
                "quality_grade": "research",
                "count": 5,
            },
            {
                "id": 2,
                "geojson": {"coordinates": [-118.6, 34.1]},
                "observed_on": "2026-03-15",
                "taxon": {"preferred_common_name": "Common Dolphin"},
                "quality_grade": "needs_id",
                "count": 3,
            },
        ]

        mock_session = MagicMock()

        with patch(
            "inaturalist.find_nearest_location",
            AsyncMock(return_value=(1, None)),
        ):
            records = await scraper._aggregate(observations, date(2026, 3, 15))

        assert len(records) == 1
        record = records[0]
        assert record["source"] == "inaturalist"
        assert record["location_id"] == 1
        assert record["species"] == "Common Dolphin"
        assert record["sighting_date"] == date(2026, 3, 15)
        assert record["count"] == 8
        assert record["source_url"] is None
        assert record["metadata"]["obs_count"] == 2
        assert record["metadata"]["obs_ids"] == [1, 2]

    @pytest.mark.asyncio
    async def test_aggregate_different_species_different_rows(self):
        """Test that different species produce different aggregate rows."""
        scraper = INatScraper()

        observations = [
            {
                "id": 10,
                "geojson": {"coordinates": [-118.5, 34.0]},
                "observed_on": "2026-03-15",
                "taxon": {"preferred_common_name": "Common Dolphin"},
                "quality_grade": "research",
                "count": 5,
            },
            {
                "id": 11,
                "geojson": {"coordinates": [-118.5, 34.0]},
                "observed_on": "2026-03-15",
                "taxon": {"preferred_common_name": "Gray Whale"},
                "quality_grade": "research",
                "count": 2,
            },
        ]

        mock_session = MagicMock()

        with patch(
            "inaturalist.find_nearest_location",
            AsyncMock(return_value=(1, None)),
        ):
            records = await scraper._aggregate(observations, date(2026, 3, 15))

        assert len(records) == 2
        species_list = sorted(r["species"] for r in records)
        assert species_list == ["Common Dolphin", "Gray Whale"]

    @pytest.mark.asyncio
    async def test_scrape_method_returns_list(self):
        """Test that the scrape method returns a list."""
        scraper = INatScraper()

        with patch.object(scraper, "_aggregate", AsyncMock(return_value=[])):
            with patch.object(scraper.http_client, "get") as mock_get:
                mock_response = MagicMock()
                mock_response.json.return_value = {"results": [], "total_results": 0}
                mock_response.raise_for_status = MagicMock()
                mock_get.return_value = mock_response

                result = await scraper.scrape()
                assert isinstance(result, list)


class TestINatTaxonIDs:
    """Test that taxon IDs are correct for marine/coastal wildlife."""

    def test_cetacea_id(self):
        """Cetacea (whales/dolphins) should be 152871."""
        cetacea_ids = [tid for tid, name in INAT_TAXA if "Cetacea" in name]
        assert len(cetacea_ids) == 1
        assert cetacea_ids[0] == 152871

    def test_pinnipeds_id(self):
        """Pinnipeds (seals/sea lions) should be 372843."""
        pinniped_ids = [tid for tid, name in INAT_TAXA if "Phocoidea" in name]
        assert len(pinniped_ids) == 1
        assert pinniped_ids[0] == 372843

    def test_no_plantae(self):
        """Taxa should not include plants (47126)."""
        taxon_ids = [tid for tid, _ in INAT_TAXA]
        assert 47126 not in taxon_ids

    def test_no_mollusca(self):
        """Taxa should not include Mollusca (47115) as marine mammals."""
        taxon_ids = [tid for tid, _ in INAT_TAXA]
        assert 47115 not in taxon_ids

    def test_enhydra_id(self):
        """Enhydra (sea otters) should be 41859."""
        otter_ids = [tid for tid, name in INAT_TAXA if "Enhydra" in name]
        assert len(otter_ids) == 1
        assert otter_ids[0] == 41859

    def test_malacostraca_id(self):
        """Malacostraca (crabs, lobsters) should be 47187."""
        crab_ids = [tid for tid, name in INAT_TAXA if "Malacostraca" in name]
        assert len(crab_ids) == 1
        assert crab_ids[0] == 47187
