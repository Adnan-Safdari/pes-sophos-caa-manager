from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from sophos_caa.core.detector import PortalDetector
from sophos_caa.core.state import NetworkInfo


def test_probe_uses_configured_endpoint_and_accepts_http_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = MagicMock(status=204)
    connection = MagicMock()
    connection.getresponse.return_value = response
    constructor = MagicMock(return_value=connection)
    monkeypatch.setattr("sophos_caa.core.detector.http.client.HTTPConnection", constructor)

    assert PortalDetector("portal.test", 8090, 0.5).probe() is True

    constructor.assert_called_once_with("portal.test", 8090, timeout=0.5)
    connection.request.assert_called_once_with(
        "HEAD",
        "/",
        headers={"User-Agent": "sophos-caa-manager/0.1"},
    )
    response.read.assert_called_once_with()
    connection.close.assert_called_once_with()


def test_probe_returns_false_and_closes_connection_on_os_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = MagicMock()
    connection.request.side_effect = OSError("unreachable")
    monkeypatch.setattr(
        "sophos_caa.core.detector.http.client.HTTPConnection",
        MagicMock(return_value=connection),
    )

    assert PortalDetector().probe() is False
    connection.close.assert_called_once_with()


@pytest.mark.parametrize("reachable", [True, False])
def test_is_caa_network_uses_snapshot_probe_result(reachable: bool) -> None:
    network = NetworkInfo(portal_reachable=reachable)
    assert PortalDetector().is_caa_network(network) is reachable
