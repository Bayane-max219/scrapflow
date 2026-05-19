from datetime import datetime, timezone, timedelta

from app.models.scraping_session import ScrapingSession


def test_duration_seconds_returns_none_when_not_finished():
    session = ScrapingSession()
    session.started_at = datetime.now(timezone.utc)
    session.finished_at = None

    assert session.duration_seconds is None


def test_duration_seconds_returns_correct_value():
    start = datetime(2026, 5, 19, 10, 0, 0, tzinfo=timezone.utc)
    end = start + timedelta(seconds=75)

    session = ScrapingSession()
    session.started_at = start
    session.finished_at = end

    assert session.duration_seconds == 75


def test_duration_seconds_exact_one_minute():
    start = datetime(2026, 5, 19, 8, 0, 0, tzinfo=timezone.utc)
    end = start + timedelta(minutes=1)

    session = ScrapingSession()
    session.started_at = start
    session.finished_at = end

    assert session.duration_seconds == 60
