import logging
from typing import Any

from app.models.scraping_job import ScraperEngine
from app.services.playwright_scraper import PlaywrightScraper
from app.services.selenium_scraper import SeleniumScraper

logger = logging.getLogger(__name__)


class ScraperDispatcher:
    """
    Routes scraping jobs to the right engine with automatic Selenium fallback
    when Playwright fails (bot detection, JS timeout, network error).
    """

    async def run(
        self,
        engine: ScraperEngine,
        url: str,
        css_selector: str | None = None,
        xpath_selector: str | None = None,
        max_pages: int = 1,
        delay_seconds: int = 2,
        proxy: str | None = None,
    ) -> tuple[list[dict[str, Any]], str]:
        """
        Returns (items, engine_used).
        Falls back to Selenium if Playwright raises an exception.
        """
        if engine == ScraperEngine.PLAYWRIGHT:
            try:
                logger.info("Starting Playwright scraper for %s", url)
                items = await self._run_playwright(url, css_selector, xpath_selector, max_pages, delay_seconds, proxy)
                return items, "playwright"
            except Exception as exc:
                logger.warning("Playwright failed (%s), falling back to Selenium", exc)
                items = self._run_selenium(url, css_selector, xpath_selector, max_pages, delay_seconds, proxy)
                return items, "selenium_fallback"

        if engine == ScraperEngine.SELENIUM:
            logger.info("Starting Selenium scraper for %s", url)
            items = self._run_selenium(url, css_selector, xpath_selector, max_pages, delay_seconds, proxy)
            return items, "selenium"

        raise ValueError(f"Unsupported engine: {engine}")

    async def _run_playwright(
        self, url: str, css: str | None, xpath: str | None, max_pages: int, delay: int, proxy: str | None
    ) -> list[dict[str, Any]]:
        scraper = PlaywrightScraper()
        return await scraper.scrape(url, css, xpath, max_pages, delay, proxy)

    def _run_selenium(
        self, url: str, css: str | None, xpath: str | None, max_pages: int, delay: int, proxy: str | None
    ) -> list[dict[str, Any]]:
        scraper = SeleniumScraper()
        return scraper.scrape(url, css, xpath, max_pages, delay, proxy)
