"""Base scraper class with retry logic and common utilities."""

from abc import ABC, abstractmethod
from typing import Any, List, Dict
import httpx


class BaseScraper(ABC):
    """Abstract base class for all Pacifica scrapers."""

    def __init__(self, name: str):
        self.name = name
        self.http_client = httpx.AsyncClient()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.http_client.aclose()

    @abstractmethod
    async def scrape(self) -> List[Dict[str, Any]]:
        """Scrape data from source. Must be implemented by subclasses."""
        pass

    async def run(self):
        """Execute the scraper."""
        print(f"[{self.name}] Starting scrape...")
        try:
            data = await self.scrape()
            print(f"[{self.name}] Successfully scraped {len(data)} items")
            return data
        except Exception as e:
            print(f"[{self.name}] Scraper failed with error: {e}")
            raise
