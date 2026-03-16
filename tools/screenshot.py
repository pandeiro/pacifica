from pathlib import Path
from datetime import datetime
from typing import Optional
from playwright.sync_api import sync_playwright

# Screenshots directory
SCREENSHOTS_DIR = Path("/Users/mu/Repos/pacifica/screenshots")


def take_screenshot(
    url: str = "http://localhost:4901", filename: Optional[str] = None
) -> Path:
    """Take a screenshot of the dashboard and save to screenshots directory."""
    # Ensure screenshots directory exists
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    # Generate filename with timestamp if not provided
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"dashboard_{timestamp}.png"

    screenshot_path = SCREENSHOTS_DIR / filename

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto(url)
        page.wait_for_load_state("networkidle")

        # Take full page screenshot
        page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"Screenshot saved to {screenshot_path}")

        browser.close()

    return screenshot_path


if __name__ == "__main__":
    take_screenshot()
