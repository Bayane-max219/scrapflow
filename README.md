# ScrapFlow — Distributed Web Scraping Platform

FastAPI + Celery distributed web scraping platform with dual-engine (Playwright + Selenium), proxy rotation, anti-detection, and async job scheduling.

## Stack

- **API**: FastAPI 0.115 + Uvicorn
- **ORM**: SQLAlchemy 2.0 async + asyncpg
- **Database**: PostgreSQL 16
- **Task queue**: Celery 5.4 + Redis 7
- **Scraping engines**: Playwright (async) + Selenium (sync) with fallback
- **Proxy rotation**: Weighted selection + EMA health scoring + auto-disable
- **Anti-detection**: 22 real User-Agents, viewport randomization, JS fingerprint masking
- **Migrations**: Alembic
- **Monitoring**: Flower dashboard
- **Tests**: pytest + pytest-asyncio (14 tests)
- **Containerization**: Docker + Docker Compose (6 services)

## Features

- Scraping job CRUD with FSM (pending → running → completed / failed)
- Dual engine dispatch: Playwright first → Selenium fallback on error
- Cron scheduling with `croniter` (auto-dispatch every minute via Celery Beat)
- Proxy pool management (add, test, rotate with weighted random selection)
- Anti-detection: real browser profiles, human-like delays (Gaussian noise), WebDriver masking, canvas fingerprint blur
- Scraped items with content-hash deduplication
- Paginated results API
- Health check endpoint
- Flower monitoring dashboard at `:5555`

## Architecture

```
scrapflow/
├── app/
│   ├── api/v1/endpoints/     ← health, jobs, proxies, items
│   ├── core/config.py        ← settings (env vars)
│   ├── db/base.py            ← async engine + get_db()
│   ├── models/               ← ScrapingJob, ScrapedItem, ProxyPool, ScrapingSession
│   ├── schemas/              ← Pydantic v2 request/response
│   ├── services/
│   │   ├── playwright_scraper.py    ← async scraper + anti-detection
│   │   ├── selenium_scraper.py      ← sync scraper
│   │   ├── scraper_dispatcher.py    ← Playwright → Selenium fallback
│   │   ├── proxy_rotation_service.py ← EMA scoring + weighted selection
│   │   └── anti_detection.py        ← browser profiles + JS init script
│   ├── tasks/
│   │   ├── celery_app.py     ← Celery config + beat schedule
│   │   └── scraping_tasks.py ← run_scraping_job + dispatch + cleanup
│   └── main.py               ← FastAPI app + lifespan
├── alembic/                  ← async migrations
├── tests/                    ← 14 pytest tests
└── docker-compose.yml        ← 6 services
```

## Run with Docker

```bash
docker compose up --build
```

Services:
| Service | URL |
|---------|-----|
| FastAPI API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Flower (Celery monitor) | http://localhost:5555 |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

Run Alembic migrations after start:

```bash
docker exec scrapflow-api alembic upgrade head
```

## Run locally

```bash
# Requirements: Python 3.11+, PostgreSQL, Redis

pip install -r requirements.txt
playwright install chromium

# Configure .env
cp .env.example .env  # edit DATABASE_URL, REDIS_URL

alembic upgrade head
uvicorn app.main:app --reload
```

Celery worker (separate terminal):

```bash
celery -A app.tasks.celery_app worker --loglevel=info -Q scraping,beat
```

Celery beat scheduler (separate terminal):

```bash
celery -A app.tasks.celery_app beat --loglevel=info
```

## Run tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Result: **14/14 tests passing**

## Key API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/v1/jobs` | List scraping jobs |
| POST | `/api/v1/jobs` | Create job |
| POST | `/api/v1/jobs/{id}/run` | Trigger job manually |
| GET | `/api/v1/items` | List scraped items (paginated) |
| GET | `/api/v1/proxies` | List proxy pool |
| POST | `/api/v1/proxies/health-check` | Health check all proxies |

## Author

**Bayane Miguel Singcol** — Fullstack Developer  
GitHub: [Bayane-max219](https://github.com/Bayane-max219)  
Portfolio: [portfolio-python-ten.vercel.app](https://portfolio-python-ten.vercel.app)
