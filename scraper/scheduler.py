"""Scraper Scheduler - APScheduler-based orchestration for all Pacifica scrapers.

This module auto-discovers all scraper classes and schedules them according
to their `schedule` cron expressions.
"""

import asyncio
import importlib
import inspect
import os
import sys
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Import BaseScraper to identify scraper classes
from base import BaseScraper


def discover_scrapers() -> list:
    """Auto-discover all scraper classes in the current directory.

    Returns a list of tuples: (scraper_class, schedule_cron)
    """
    scrapers = []
    current_dir = Path(__file__).parent

    # Get all Python files in the scraper directory (excluding base.py and scheduler.py)
    for file_path in current_dir.glob("*.py"):
        module_name = file_path.stem

        # Skip non-scraper files
        if module_name in ("base", "scheduler", "__init__"):
            continue

        try:
            # Import the module
            module = importlib.import_module(module_name)

            # Find all BaseScraper subclasses
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (
                    issubclass(obj, BaseScraper)
                    and obj is not BaseScraper
                    and hasattr(obj, "schedule")
                ):
                    schedule = getattr(obj, "schedule", None)
                    if schedule:
                        scrapers.append((obj, schedule))
                        print(
                            f"[Scheduler] Discovered scraper: {name} with schedule '{schedule}'"
                        )
                    else:
                        print(
                            f"[Scheduler] Warning: {name} has no schedule attribute, skipping"
                        )

        except Exception as e:
            print(f"[Scheduler] Error loading module {module_name}: {e}")
            continue

    return scrapers


def parse_cron(cron_expr: str) -> dict:
    """Parse a cron expression into kwargs for APScheduler CronTrigger.

    Supports standard cron format: minute hour day month day_of_week
    Example: "0 2 * * *" = daily at 2:00 AM
    """
    parts = cron_expr.split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression: {cron_expr}. Expected 5 fields.")

    return {
        "minute": parts[0],
        "hour": parts[1],
        "day": parts[2],
        "month": parts[3],
        "day_of_week": parts[4],
    }


async def run_scraper(scraper_class):
    """Execute a single scraper run."""
    scraper_name = scraper_class.__name__
    print(f"[Scheduler] Running {scraper_name}...")

    try:
        scraper = scraper_class()
        records = await scraper.run()
        print(f"[Scheduler] {scraper_name} completed: {len(records)} records scraped")
    except Exception as e:
        print(f"[Scheduler] {scraper_name} failed: {e}")
        # Don't re-raise - we want the scheduler to continue even if one scraper fails


async def main():
    """Main entry point - set up and run the scheduler."""
    print("=" * 60)
    print("Pacifica Scraper Scheduler")
    print("=" * 60)

    # Discover all scrapers
    scrapers = discover_scrapers()

    if not scrapers:
        print("[Scheduler] No scrapers found! Exiting.")
        return

    print(f"[Scheduler] Loaded {len(scrapers)} scraper(s)")
    print("-" * 60)

    # Create the scheduler
    scheduler = AsyncIOScheduler()

    # Add each scraper to the scheduler
    for scraper_class, schedule in scrapers:
        try:
            cron_kwargs = parse_cron(schedule)
            trigger = CronTrigger(**cron_kwargs)

            # Add the job
            scheduler.add_job(
                run_scraper,
                trigger=trigger,
                args=[scraper_class],
                id=scraper_class.__name__,
                name=f"{scraper_class.__name__} scraper",
                replace_existing=True,
                max_instances=1,  # Don't run the same scraper concurrently
            )

            print(f"[Scheduler] Scheduled {scraper_class.__name__}: {schedule}")

        except Exception as e:
            print(f"[Scheduler] Error scheduling {scraper_class.__name__}: {e}")
            continue

    print("-" * 60)
    print("[Scheduler] Starting scheduler...")
    scheduler.start()

    # Run immediately on startup for testing (optional - remove in production)
    print("[Scheduler] Running all scrapers once on startup...")
    for scraper_class, _ in scrapers:
        await run_scraper(scraper_class)

    print("[Scheduler] Scheduler is running. Press Ctrl+C to exit.")
    print("=" * 60)

    # Keep the event loop running
    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        print("\n[Scheduler] Shutting down...")
        scheduler.shutdown()
        print("[Scheduler] Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())
