"""
Advanced anti-detection helpers for ScrapFlow scrapers.
Provides realistic browser fingerprint randomization and human-like timing.
"""
import random
import time
from dataclasses import dataclass, field

# Real-world user agent distributions (Jan 2026)
_DESKTOP_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 OPR/115.0.0.0",
]

_MOBILE_AGENTS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.6778.39 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.58 Mobile Safari/537.36",
]

_VIEWPORTS_DESKTOP = [
    (1920, 1080), (1440, 900), (1366, 768), (1536, 864), (2560, 1440), (1280, 800),
]

_VIEWPORTS_MOBILE = [
    (390, 844), (414, 896), (393, 852), (375, 812),
]

_ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.9",
    "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "de-DE,de;q=0.9,en;q=0.8",
    "es-ES,es;q=0.9,en;q=0.8",
    "en-US,en;q=0.9,fr;q=0.8",
]

_ACCEPT_ENCODINGS = [
    "gzip, deflate, br, zstd",
    "gzip, deflate, br",
    "gzip, deflate",
]


@dataclass
class BrowserProfile:
    """A consistent fingerprint profile for a single scraping session."""
    user_agent: str
    viewport_width: int
    viewport_height: int
    accept_language: str
    accept_encoding: str
    is_mobile: bool
    platform: str
    extra_headers: dict = field(default_factory=dict)


def generate_profile(mobile: bool = False) -> BrowserProfile:
    """Generates a consistent randomized browser profile for one session."""
    if mobile:
        ua = random.choice(_MOBILE_AGENTS)
        w, h = random.choice(_VIEWPORTS_MOBILE)
        platform = "Linux armv81" if "Android" in ua else "iPhone"
    else:
        ua = random.choice(_DESKTOP_AGENTS)
        w, h = random.choice(_VIEWPORTS_DESKTOP)
        if "Windows" in ua:
            platform = "Win32"
        elif "Mac" in ua:
            platform = "MacIntel"
        else:
            platform = "Linux x86_64"

    lang = random.choice(_ACCEPT_LANGUAGES)

    extra_headers: dict[str, str] = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": lang,
        "Accept-Encoding": random.choice(_ACCEPT_ENCODINGS),
        "Cache-Control": random.choice(["no-cache", "max-age=0"]),
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    }

    # Add Sec-CH-UA headers for Chromium-based agents
    if "Chrome" in ua or "Edg" in ua:
        chrome_version = _extract_chrome_version(ua)
        extra_headers["Sec-CH-UA"] = f'"Chromium";v="{chrome_version}", "Google Chrome";v="{chrome_version}", "Not?A_Brand";v="99"'
        extra_headers["Sec-CH-UA-Mobile"] = "?1" if mobile else "?0"
        extra_headers["Sec-CH-UA-Platform"] = f'"{platform}"'

    return BrowserProfile(
        user_agent=ua,
        viewport_width=w,
        viewport_height=h,
        accept_language=lang,
        accept_encoding=extra_headers["Accept-Encoding"],
        is_mobile=mobile,
        platform=platform,
        extra_headers=extra_headers,
    )


def human_delay(base_seconds: float, variance: float = 0.4) -> float:
    """
    Computes a human-like delay with Gaussian noise around the base value.
    Returns actual delay applied (seconds).
    """
    jitter = random.gauss(0, base_seconds * variance)
    actual = max(0.3, base_seconds + jitter)
    time.sleep(actual)
    return actual


async def async_human_delay(base_seconds: float, variance: float = 0.4) -> float:
    """Async version of human_delay."""
    import asyncio
    jitter = random.gauss(0, base_seconds * variance)
    actual = max(0.3, base_seconds + jitter)
    await asyncio.sleep(actual)
    return actual


def get_playwright_init_script(profile: BrowserProfile) -> str:
    """
    Returns a JS init script that masks Playwright/CDP fingerprints.
    Inject via page.add_init_script() before navigation.
    """
    return f"""
    // Mask webdriver
    Object.defineProperty(navigator, 'webdriver', {{ get: () => undefined }});

    // Override platform
    Object.defineProperty(navigator, 'platform', {{ get: () => '{profile.platform}' }});

    // Mask automation plugins
    Object.defineProperty(navigator, 'plugins', {{
        get: () => [
            {{ name: 'PDF Viewer', filename: 'internal-pdf-viewer' }},
            {{ name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' }},
            {{ name: 'Chromium PDF Viewer', filename: 'internal-pdf-viewer' }},
        ]
    }});

    // Hide Playwright runtime
    window.chrome = {{ runtime: {{}} }};

    // Randomize canvas fingerprint slightly
    const origGetContext = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function(type, attrs) {{
        const ctx = origGetContext.call(this, type, attrs);
        if (type === '2d' && ctx) {{
            const origFillText = ctx.fillText.bind(ctx);
            ctx.fillText = function(text, x, y, maxW) {{
                origFillText(text, x + Math.random() * 0.01, y + Math.random() * 0.01, maxW);
            }};
        }}
        return ctx;
    }};

    // Realistic screen dimensions
    Object.defineProperty(window.screen, 'width', {{ get: () => {profile.viewport_width} }});
    Object.defineProperty(window.screen, 'height', {{ get: () => {profile.viewport_height} }});
    Object.defineProperty(window.screen, 'availWidth', {{ get: () => {profile.viewport_width} }});
    Object.defineProperty(window.screen, 'availHeight', {{ get: () => {profile.viewport_height - 40} }});
    """


def _extract_chrome_version(ua: str) -> str:
    """Extracts major Chrome version from a user-agent string."""
    import re
    match = re.search(r"Chrome/(\d+)", ua)
    return match.group(1) if match else "131"
