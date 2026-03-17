"""Tests for the South Coast Divers Scraper."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add the scraper directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "scraper"))

from south_coast_divers import SouthCoastDiversScraper


class MockLocation:
    """Mock Location object for testing."""
    def __init__(self):
        self.id = 1
        self.name = "Shaws Cove"
        self.slug = "shaws_cove"


class TestSouthCoastDiversScraper:
    """Test suite for the South Coast Divers Scraper."""

    def test_scraper_initialization(self):
        """Test that the scraper initializes correctly."""
        scraper = SouthCoastDiversScraper()
        assert scraper.name == "south_coast_divers"
        assert scraper.schedule == "0 */3 * * *"
        assert scraper.location_slug == "shaws_cove"
        assert scraper.url == "https://southcoastdivers.com/"

    def test_extract_dive_report_with_valid_html(self):
        """Test extraction of dive report from valid HTML structure."""
        scraper = SouthCoastDiversScraper()
        
        # Create sample HTML matching the expected structure
        sample_html = """
        <html>
        <body>
            <div>
                <p>Here is the latest group post.</p>
                <table>
                    <tr>
                        <td>Water temp: 65°F</td>
                        <td>Visibility: 15ft</td>
                    </tr>
                    <tr>
                        <td>Conditions: Flat, clear</td>
                    </tr>
                </table>
            </div>
        </body>
        </html>
        """
        
        result = scraper._extract_dive_report(sample_html)
        
        assert result is not None
        assert "Water temp: 65°F" in result
        assert "Visibility: 15ft" in result
        assert "Conditions: Flat, clear" in result

    def test_extract_dive_report_with_no_target_text(self):
        """Test extraction when target text is not found."""
        scraper = SouthCoastDiversScraper()
        
        # HTML without the target text
        sample_html = """
        <html>
        <body>
            <table>
                <tr><td>Some other content</td></tr>
            </table>
        </body>
        </html>
        """
        
        result = scraper._extract_dive_report(sample_html)
        
        assert result is None

    def test_extract_dive_report_with_no_table(self):
        """Test extraction when target text exists but no table follows."""
        scraper = SouthCoastDiversScraper()
        
        # HTML with target text but no table
        sample_html = """
        <html>
        <body>
            <p>Here is the latest group post.</p>
            <div>No table here</div>
        </body>
        </html>
        """
        
        result = scraper._extract_dive_report(sample_html)
        
        assert result is None

    def test_extract_dive_report_preserves_structure(self):
        """Test that table structure is preserved in extraction."""
        scraper = SouthCoastDiversScraper()
        
        # Create sample HTML with multiple rows and columns
        sample_html = """
        <html>
        <body>
            <p>Here is the latest group post.</p>
            <table>
                <tr>
                    <th>Parameter</th>
                    <th>Value</th>
                </tr>
                <tr>
                    <td>Temp</td>
                    <td>64°F</td>
                </tr>
                <tr>
                    <td>Vis</td>
                    <td>20ft</td>
                </tr>
            </table>
        </body>
        </html>
        """
        
        result = scraper._extract_dive_report(sample_html)
        
        assert result is not None
        # Check that pipe separator is used for columns
        assert " | " in result
        assert "Parameter | Value" in result
        assert "Temp | 64°F" in result

    @pytest.mark.asyncio
    async def test_scrape_with_duplicate_detection(self):
        """Test that duplicate reports are not inserted."""
        scraper = SouthCoastDiversScraper()
        
        # Mock the database functions
        mock_location = MockLocation()
        
        with patch('south_coast_divers.get_db_session') as mock_session:
            # Setup mock context manager
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            
            # Mock location lookup
            with patch('south_coast_divers.get_location_by_slug', new_callable=AsyncMock) as mock_get_loc:
                mock_get_loc.return_value = mock_location
                
                # Mock duplicate check returning True (duplicate found)
                with patch('south_coast_divers.check_duplicate_dive_report', new_callable=AsyncMock) as mock_check_dup:
                    mock_check_dup.return_value = True
                    
                    # Mock the HTML fetching
                    sample_html = """
                    <html>
                    <body>
                        <p>Here is the latest group post.</p>
                        <table>
                            <tr><td>Test report</td></tr>
                        </table>
                    </body>
                    </html>
                    """
                    with patch.object(scraper, '_fetch_page', new_callable=AsyncMock) as mock_fetch:
                        mock_fetch.return_value = sample_html
                        
                        result = await scraper.scrape()
                        
                        # Should return empty list due to duplicate detection
                        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_scrape_successful_insertion(self):
        """Test successful scraping and insertion of new dive report."""
        scraper = SouthCoastDiversScraper()
        
        mock_location = MockLocation()
        
        with patch('south_coast_divers.get_db_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            
            with patch('south_coast_divers.get_location_by_slug', new_callable=AsyncMock) as mock_get_loc:
                mock_get_loc.return_value = mock_location
                
                # Mock duplicate check returning False (no duplicate)
                with patch('south_coast_divers.check_duplicate_dive_report', new_callable=AsyncMock) as mock_check_dup:
                    mock_check_dup.return_value = False
                    
                    # Mock insert_conditions
                    with patch('south_coast_divers.insert_conditions', new_callable=AsyncMock) as mock_insert:
                        sample_html = """
                        <html>
                        <body>
                            <p>Here is the latest group post.</p>
                            <table>
                                <tr><td>New dive report</td></tr>
                            </table>
                        </body>
                        </html>
                        """
                        with patch.object(scraper, '_fetch_page', new_callable=AsyncMock) as mock_fetch:
                            mock_fetch.return_value = sample_html
                            
                            result = await scraper.scrape()
                            
                            # Should return one record
                            assert len(result) == 1
                            assert result[0]['condition_type'] == 'dive_report'
                            assert result[0]['source'] == 'south_coast_divers'
                            assert 'New dive report' in result[0]['raw_text']
                            
                            # Verify insert was called
                            mock_insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_scrape_with_missing_location(self):
        """Test scraping when location is not found in database."""
        scraper = SouthCoastDiversScraper()
        
        with patch('south_coast_divers.get_db_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            
            with patch('south_coast_divers.get_location_by_slug', new_callable=AsyncMock) as mock_get_loc:
                mock_get_loc.return_value = None
                
                result = await scraper.scrape()
                
                # Should return empty list when location not found
                assert len(result) == 0

    @pytest.mark.asyncio
    async def test_scrape_with_fetch_error(self):
        """Test scraping when HTTP fetch fails."""
        scraper = SouthCoastDiversScraper()
        
        mock_location = MockLocation()
        
        with patch('south_coast_divers.get_db_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            
            with patch('south_coast_divers.get_location_by_slug', new_callable=AsyncMock) as mock_get_loc:
                mock_get_loc.return_value = mock_location
                
                with patch.object(scraper, '_fetch_page', new_callable=AsyncMock) as mock_fetch:
                    mock_fetch.side_effect = Exception("HTTP Error")
                    
                    result = await scraper.scrape()
                    
                    # Should return empty list when fetch fails
                    assert len(result) == 0
