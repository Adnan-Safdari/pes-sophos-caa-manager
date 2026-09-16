from __future__ import annotations

import pytest

from sophos_caa.core.state import Connectivity
from sophos_caa.network.connectivity import from_nm_value


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, Connectivity.UNKNOWN),
        (1, Connectivity.NONE),
        (2, Connectivity.PORTAL),
        (3, Connectivity.LIMITED),
        (4, Connectivity.FULL),
        (5, Connectivity.UNKNOWN),
        (-1, Connectivity.UNKNOWN),
    ],
)
def test_networkmanager_connectivity_mapping(value: int, expected: Connectivity) -> None:
    assert from_nm_value(value) is expected
