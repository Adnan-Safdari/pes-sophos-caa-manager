"""NetworkManager connectivity value normalization."""

from sophos_caa.core.state import Connectivity


def from_nm_value(value: int) -> Connectivity:
    return {
        1: Connectivity.NONE,
        2: Connectivity.PORTAL,
        3: Connectivity.LIMITED,
        4: Connectivity.FULL,
    }.get(value, Connectivity.UNKNOWN)
