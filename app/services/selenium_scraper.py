import hashlib
import random
import time
from typing import Any

from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

ua = UserAgent()


class SeleniumScraper:
    def __init__(self):
        self._driver: webdriver.Chrome | None = None

    def _launch(self, proxy: str | None = None) -> None:
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument(f"user-agent={ua.random}")
        options.add_argument("--window-size=1366,768")

        if proxy:
            options.add_argument(f"--proxy-server={proxy}")

        service = Service(ChromeDriverManager().install())
        self._driver = webdriver.Chrome(service=service, options=options)
        self._driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    def _close(self) -> None:
        if self._driver:
            self._driver.quit()
            self._driver = None

    def scrape(
        self,
        url: str,
        css_selector: str | None = None,
        xpath_selector: str | None = None,
        max_pages: int = 1,
        delay_seconds: int = 2,
        proxy: str | None = None,
    ) -> list[dict[str, Any]]:
        self._launch(proxy=proxy)
        results: list[dict[str, Any]] = []

        try:
            current_url = url
            for page_num in range(1, max_pages + 1):
                self._driver.get(current_url)
                WebDriverWait(self._driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                time.sleep(random.uniform(delay_seconds * 0.8, delay_seconds * 1.2))

                items = self._extract_items(css_selector, xpath_selector)
                for item in items:
                    item["source_url"] = current_url
                    item["page_num"] = page_num
                    item["content_hash"] = self._hash(item)
                results.extend(items)

                next_url = self._find_next_page()
                if not next_url or page_num >= max_pages:
                    break
                current_url = next_url
        finally:
            self._close()

        return results

    def _extract_items(self, css_selector: str | None, xpath_selector: str | None) -> list[dict[str, Any]]:
        if css_selector:
            elements = self._driver.find_elements(By.CSS_SELECTOR, css_selector)
            return [{"text": el.text, "html": el.get_attribute("innerHTML")} for el in elements]

        if xpath_selector:
            elements = self._driver.find_elements(By.XPATH, xpath_selector)
            return [{"text": el.text, "html": el.get_attribute("innerHTML")} for el in elements]

        title = self._driver.title
        content = self._driver.find_element(By.TAG_NAME, "body").text
        return [{"title": title, "content": content[:5000]}]

    def _find_next_page(self) -> str | None:
        selectors = [
            (By.CSS_SELECTOR, "a[rel='next']"),
            (By.CSS_SELECTOR, ".pagination .next a"),
            (By.CSS_SELECTOR, "a.page-next"),
            (By.XPATH, "//a[@aria-label='Next page']"),
        ]
        for by, selector in selectors:
            try:
                el = self._driver.find_element(by, selector)
                href = el.get_attribute("href")
                if href:
                    return href
            except Exception:
                continue
        return None

    @staticmethod
    def _hash(item: dict[str, Any]) -> str:
        content = str(item.get("text", "")) + str(item.get("content", ""))
        return hashlib.sha256(content.encode()).hexdigest()
