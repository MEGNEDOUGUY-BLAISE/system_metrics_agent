import pytest

from app.config import Settings


def test_from_env_defaults(monkeypatch):
    monkeypatch.delenv("METRICS_ENDPOINT", raising=False)
    monkeypatch.delenv("COLLECTION_INTERVAL", raising=False)
    monkeypatch.delenv("REQUEST_TIMEOUT", raising=False)

    settings = Settings.from_env()

    assert settings.metrics_endpoint == "http://127.0.0.1:8000/metrics"
    assert settings.collection_interval == 5.0
    assert settings.request_timeout == 5.0


def test_from_env_custom_values(monkeypatch):
    monkeypatch.setenv("METRICS_ENDPOINT", "http://api:8000/metrics")
    monkeypatch.setenv("COLLECTION_INTERVAL", "10")
    monkeypatch.setenv("REQUEST_TIMEOUT", "2.5")

    settings = Settings.from_env()

    assert settings.metrics_endpoint == "http://api:8000/metrics"
    assert settings.collection_interval == 10.0
    assert settings.request_timeout == 2.5


def test_from_env_non_numeric(monkeypatch):
    monkeypatch.setenv("COLLECTION_INTERVAL", "abc")

    with pytest.raises(ValueError):
        Settings.from_env()


@pytest.mark.parametrize("interval,timeout", [("0", "5"), ("5", "-1")])
def test_from_env_non_positive(monkeypatch, interval, timeout):
    monkeypatch.setenv("COLLECTION_INTERVAL", interval)
    monkeypatch.setenv("REQUEST_TIMEOUT", timeout)

    with pytest.raises(ValueError):
        Settings.from_env()
