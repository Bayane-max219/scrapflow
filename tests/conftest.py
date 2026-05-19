import pytest
from unittest.mock import AsyncMock, MagicMock

from app.models.scraping_job import ScraperEngine, JobStatus, ScrapingJob
from app.models.proxy_pool import ProxyPool, ProxyProtocol
from app.models.scraping_session import ScrapingSession


@pytest.fixture
def sample_job() -> ScrapingJob:
    job = MagicMock(spec=ScrapingJob)
    job.id = 1
    job.name = "Test Job"
    job.target_url = "https://example.com"
    job.status = JobStatus.PENDING
    job.engine = ScraperEngine.PLAYWRIGHT
    job.css_selector = ".item"
    job.xpath_selector = None
    job.max_pages = 3
    job.delay_seconds = 1
    return job


@pytest.fixture
def sample_proxy() -> ProxyPool:
    proxy = MagicMock(spec=ProxyPool)
    proxy.id = 1
    proxy.host = "proxy.example.com"
    proxy.port = 8080
    proxy.protocol = ProxyProtocol.HTTP
    proxy.username = None
    proxy.password = None
    proxy.is_active = True
    proxy.success_rate = 0.95
    proxy.response_time_ms = 120
    proxy.get_url.return_value = "http://proxy.example.com:8080"
    return proxy
