import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.scraping_job import ScraperEngine
from app.services.scraper_dispatcher import ScraperDispatcher


@pytest.mark.asyncio
async def test_dispatcher_routes_to_playwright():
    dispatcher = ScraperDispatcher()
    mock_items = [{"title": "Article 1", "url": "https://example.com/1"}]

    with patch.object(dispatcher, "_run_playwright", new=AsyncMock(return_value=mock_items)):
        items, engine = await dispatcher.run(
            engine=ScraperEngine.PLAYWRIGHT,
            url="https://example.com",
            css_selector=".article",
        )

    assert engine == "playwright"
    assert len(items) == 1
    assert items[0]["title"] == "Article 1"


@pytest.mark.asyncio
async def test_dispatcher_routes_to_selenium():
    dispatcher = ScraperDispatcher()
    mock_items = [{"title": "Product", "price": "19.99"}]

    with patch.object(dispatcher, "_run_selenium", return_value=mock_items):
        items, engine = await dispatcher.run(
            engine=ScraperEngine.SELENIUM,
            url="https://shop.example.com",
            css_selector=".product",
        )

    assert engine == "selenium"
    assert len(items) == 1


@pytest.mark.asyncio
async def test_dispatcher_falls_back_to_selenium_on_playwright_error():
    dispatcher = ScraperDispatcher()
    fallback_items = [{"title": "Fallback item"}]

    with (
        patch.object(dispatcher, "_run_playwright", new=AsyncMock(side_effect=Exception("bot detected"))),
        patch.object(dispatcher, "_run_selenium", return_value=fallback_items),
    ):
        items, engine = await dispatcher.run(
            engine=ScraperEngine.PLAYWRIGHT,
            url="https://protected.example.com",
        )

    assert engine == "selenium_fallback"
    assert items == fallback_items


@pytest.mark.asyncio
async def test_dispatcher_raises_on_unsupported_engine():
    dispatcher = ScraperDispatcher()

    with pytest.raises(ValueError, match="Unsupported engine"):
        await dispatcher.run(engine="ftp", url="ftp://example.com")  # type: ignore


@pytest.mark.asyncio
async def test_dispatcher_playwright_returns_empty_list():
    dispatcher = ScraperDispatcher()

    with patch.object(dispatcher, "_run_playwright", new=AsyncMock(return_value=[])):
        items, engine = await dispatcher.run(
            engine=ScraperEngine.PLAYWRIGHT,
            url="https://empty.example.com",
            css_selector=".nonexistent",
        )

    assert engine == "playwright"
    assert items == []


@pytest.mark.asyncio
async def test_dispatcher_passes_proxy_to_playwright():
    dispatcher = ScraperDispatcher()
    proxy_url = "http://proxy.example.com:8080"
    captured = {}

    async def fake_playwright(url, css, xpath, max_pages, delay, proxy):
        captured["proxy"] = proxy
        return []

    with patch.object(dispatcher, "_run_playwright", new=fake_playwright):
        await dispatcher.run(
            engine=ScraperEngine.PLAYWRIGHT,
            url="https://example.com",
            proxy=proxy_url,
        )

    assert captured["proxy"] == proxy_url
