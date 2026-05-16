import asyncio
import hashlib
import random
from typing import Any

from fake_useragent import UserAgent
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from app.core.config import settings

ua = UserAgent()


class PlaywrightScraper:
    def __init__(self):
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    async def _launch(self) -> None:
        playwright = await async_playwright().start()
        self._browser = await playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-blink-features=AutomationControlled"],
        )
        self._context = await self._browser.new_context(
            user_agent=ua.random,
            viewport={"width": 1366, "height": 768},
            locale="fr-FR",
            extra_http_headers={"Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"},
        )
        await self._context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

    async def _close(self) -> None:
        if self._browser:
            await self._browser.close()
            self._browser = None
            self._context = None

    async def scrape(
        self,
        url: str,
        css_selector: str | None = None,
        xpath_selector: str | None = None,
        max_pages: int = 1,
        delay_seconds: int = 2,
        proxy: str | None = None,
    ) -> list[dict[str, Any]]:
        await self._launch()
        results: list[dict[str, Any]] = []

        try:
            page = await self._context.new_page()
            current_url = url

            for page_num in range(1, max_pages + 1):
                await page.goto(current_url, wait_until="networkidle", timeout=30_000)

                await asyncio.sleep(random.uniform(delay_seconds * 0.8, delay_seconds * 1.2))

                items = await self._extract_items(page, css_selector, xpath_selector)
                for item in items:
                    item["source_url"] = current_url
                    item["page_num"] = page_num
                    item["content_hash"] = self._hash(item)
                results.extend(items)

                next_url = await self._find_next_page(page)
                if not next_url or page_num >= max_pages:
                    break
                current_url = next_url

            await page.close()
        finally:
            await self._close()

        return results

    async def _extract_items(
        self, page: Page, css_selector: str | None, xpath_selector: str | None
    ) -> list[dict[str, Any]]:
        if css_selector:
            elements = await page.query_selector_all(css_selector)
            return [{"text": await el.inner_text(), "html": await el.inner_html()} for el in elements]

        if xpath_selector:
            elements = await page.query_selector_all(f"xpath={xpath_selector}")
            return [{"text": await el.inner_text(), "html": await el.inner_html()} for el in elements]

        title = await page.title()
        content = await page.evaluate("() => document.body.innerText")
        return [{"title": title, "content": content[:5000]}]

    async def _find_next_page(self, page: Page) -> str | None:
        selectors = ["a[rel='next']", ".pagination .next a", "a.page-next", "[aria-label='Next page']"]
        for selector in selectors:
            el = await page.query_selector(selector)
            if el:
                href = await el.get_attribute("href")
                if href:
                    return href if href.startswith("http") else page.url.rsplit("/", 1)[0] + "/" + href
        return None

    @staticmethod
    def _hash(item: dict[str, Any]) -> str:
        content = str(item.get("text", "")) + str(item.get("content", ""))
        return hashlib.sha256(content.encode()).hexdigest()
