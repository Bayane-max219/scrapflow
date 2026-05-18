import asyncio
import hashlib
from typing import Any

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from app.services.anti_detection import async_human_delay, generate_profile, get_playwright_init_script


class PlaywrightScraper:
    def __init__(self, mobile: bool = False) -> None:
        self._profile = generate_profile(mobile=mobile)
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    async def _launch(self, proxy: str | None = None) -> None:
        playwright = await async_playwright().start()

        launch_opts: dict[str, Any] = {
            "headless": True,
            "args": [
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
        }
        if proxy:
            launch_opts["proxy"] = {"server": proxy}

        self._browser = await playwright.chromium.launch(**launch_opts)

        context_opts: dict[str, Any] = {
            "user_agent": self._profile.user_agent,
            "viewport": {"width": self._profile.viewport_width, "height": self._profile.viewport_height},
            "locale": self._profile.accept_language.split(",")[0],
            "extra_http_headers": self._profile.extra_headers,
            "is_mobile": self._profile.is_mobile,
        }

        self._context = await self._browser.new_context(**context_opts)
        await self._context.add_init_script(get_playwright_init_script(self._profile))

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
        await self._launch(proxy=proxy)
        results: list[dict[str, Any]] = []

        try:
            page = await self._context.new_page()
            current_url = url

            for page_num in range(1, max_pages + 1):
                await page.goto(current_url, wait_until="networkidle", timeout=30_000)

                # Human-like delay with Gaussian noise
                await async_human_delay(delay_seconds)

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

                # Additional inter-page delay (simulate reading time)
                await async_human_delay(delay_seconds * 0.5)

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
