from unittest.mock import patch

from app.agent import run_forever, run_once
from app.collector import MetricsCollectionError
from app.config import Settings

SETTINGS = Settings(
    metrics_endpoint="http://test/metrics",
    collection_interval=1.0,
    request_timeout=2.0,
)


@patch("app.agent.send_metrics")
@patch("app.agent.format_metrics")
@patch("app.agent.collect_system_metrics")
def test_run_once(mock_collect, mock_format, mock_send):
    mock_collect.return_value = {"cpu": {}}
    mock_format.return_value = {"agent": "x"}
    mock_send.return_value = {"status_code": 201}

    result = run_once(SETTINGS)

    assert result == {"status_code": 201}
    mock_format.assert_called_once_with({"cpu": {}})
    mock_send.assert_called_once_with(
        endpoint="http://test/metrics",
        payload={"agent": "x"},
        timeout=2.0,
    )


@patch("app.agent.time.sleep")
@patch("app.agent.run_once")
@patch("app.agent.Settings.from_env", return_value=SETTINGS)
def test_run_forever(mock_from_env, mock_run_once, mock_sleep):
    # 1er cycle : succès, 2e : erreur de collecte, 3e : arrêt (Ctrl+C)
    mock_run_once.side_effect = [
        {"status_code": 201},
        MetricsCollectionError("erreur simulée"),
        KeyboardInterrupt(),
    ]

    run_forever()

    assert mock_run_once.call_count == 3
    assert mock_sleep.call_count == 2
