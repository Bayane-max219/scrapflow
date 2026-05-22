import hashlib
import time
import random
from typing import Any
from urllib.parse import urljoin, urlparse
from html.parser import HTMLParser

import httpx

from app.services.anti_detection import generate_profile


class _TextExtractor(HTMLParser):
    """Minimal HTML parser — extracts text from matching tags."""

    def __init__(self, tag_filter: str | None = None):
        super().__init__()
        self._tag_filter = tag_filter.lower() if tag_filter else None
        self._inside = 0
        self._current: list[str] = []
        self.items: list[str] = []

    def handle_starttag(self, tag, attrs):
        if self._tag_filter is None or tag == self._tag_filter:
            self._inside += 1

    def handle_endtag(self, tag):
        if self._tag_filter is None or tag == self._tag_filter:
            if self._inside > 0:
                self._inside -= 1
                text = " ".join(self._current).strip()
                if text:
                    self.items.append(text)
                self._current = []

    def handle_data(self, data):
        if self._inside > 0:
            cleaned = data.strip()
            if cleaned:
                self._current.append(cleaned)


def _css_tag(selector: str | None) -> str | None:
    """Extract the HTML tag from a simple CSS selector like 'p', 'h1', 'a'."""
    if not selector:
        return None
    token = selector.strip().split()[0].split(".")[0].split("#")[0].split(":")[0]
    return token if token.isalpha() else None


class HttpxScraper:
    """
    Lightweight scraper using HTTPX — no browser required.
    Uses randomised headers from the anti-detection module.
    """

    def __init__(self) -> None:
        self._profile = generate_profile()

    def scrape(
        self,
        url: str,
        css_selector: str | None = None,
        xpath_selector: str | None = None,
        max_pages: int = 1,
        delay_seconds: int = 1,
        proxy: str | None = None,
    ) -> list[dict[str, Any]]:
        proxy_url = proxy or None
        headers = {
            "User-Agent": self._profile.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": self._profile.accept_language,
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        results: list[dict[str, Any]] = []
        current_url = url

        with httpx.Client(
            headers=headers,
            proxy=proxy_url,
            follow_redirects=True,
            timeout=15,
            verify=False,
        ) as client:
            for page_num in range(1, max_pages + 1):
                resp = client.get(current_url)
                resp.raise_for_status()
                html = resp.text

                items = self._extract(html, current_url, css_selector or xpath_selector)
                for item in items:
                    item["source_url"] = current_url
                    item["page_num"] = page_num
                    item["content_hash"] = hashlib.sha256(
                        item.get("text", "").encode()
                    ).hexdigest()
                results.extend(items)

                if page_num >= max_pages:
                    break

                next_url = self._find_next(html, current_url)
                if not next_url:
                    break
                current_url = next_url

                if delay_seconds > 0:
                    time.sleep(delay_seconds + random.uniform(0, 0.5))

        return results

    def _extract(self, html: str, url: str, selector: str | None) -> list[dict[str, Any]]:
        tag = _css_tag(selector)
        parser = _TextExtractor(tag_filter=tag)
        parser.feed(html)

        if parser.items:
            return [{"text": t, "url": url} for t in parser.items[:50]]

        # Fallback: extract title + meta description
        title = self._extract_title(html)
        desc = self._extract_meta(html)
        return [{"title": title, "description": desc, "url": url}]

    def _extract_title(self, html: str) -> str:
        start = html.lower().find("<title>")
        end = html.lower().find("</title>")
        if start != -1 and end != -1:
            return html[start + 7:end].strip()
        return ""

    def _extract_meta(self, html: str) -> str:
        lower = html.lower()
        idx = lower.find('name="description"')
        if idx == -1:
            idx = lower.find("name='description'")
        if idx == -1:
            return ""
        content_idx = lower.find("content=", idx)
        if content_idx == -1:
            return ""
        q = html[content_idx + 8]
        end = html.find(q, content_idx + 9)
        return html[content_idx + 9:end].strip() if end != -1 else ""

    def _find_next(self, html: str, base_url: str) -> str | None:
        lower = html.lower()
        for marker in ['rel="next"', "rel='next'"]:
            idx = lower.find(marker)
            if idx != -1:
                tag_start = html.rfind("<a", 0, idx)
                href_idx = html.lower().find("href=", tag_start)
                if href_idx != -1:
                    q = html[href_idx + 5]
                    end = html.find(q, href_idx + 6)
                    href = html[href_idx + 6:end]
                    return urljoin(base_url, href)
        return None
