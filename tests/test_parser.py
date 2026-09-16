from __future__ import annotations

import pytest

from sophos_caa.caa.parser import CAAEvent, CAAOutputParser


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("caa started in foreground mode.", CAAEvent.STARTED),
        ("Connecting to host 192.168.254.1 ...", CAAEvent.CONNECTING),
        (
            "Connected with ECDHE-RSA-AES256-GCM-SHA384 encryption.",
            CAAEvent.CONNECTED,
        ),
        ("Login was accepted.", CAAEvent.AUTHENTICATED),
        ("Running instance of caa terminated by signal 15", CAAEvent.STOPPED),
    ],
)
def test_observed_caa_messages(line: str, expected: CAAEvent) -> None:
    assert CAAOutputParser().parse_line(line) is expected


@pytest.mark.parametrize(
    "line",
    [
        "Client type sent: Linux",
        "OK Notification received.",
        "PONG sent!",
        "7 IPv4 addresses sent!",
        "",
    ],
)
def test_other_observed_output_is_unknown(line: str) -> None:
    assert CAAOutputParser().parse_line(line) is CAAEvent.UNKNOWN


def test_parser_ignores_surrounding_whitespace() -> None:
    assert CAAOutputParser().parse_line("  Login was accepted.\n") is CAAEvent.AUTHENTICATED
