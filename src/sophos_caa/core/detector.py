"""PES network detector abstraction."""

from __future__ import annotations

import http.client
from dataclasses import dataclass
from typing import Protocol

from .state import NetworkInfo


class NetworkDetector(Protocol):
    def is_caa_network(self, network: NetworkInfo) -> bool: ...


@dataclass(frozen=True, slots=True)
class PortalDetector:
    host: str = "192.168.254.1"
    port: int = 8090
    timeout: float = 2.0

    def probe(self) -> bool:
        connection = http.client.HTTPConnection(self.host, self.port, timeout=self.timeout)
        try:
            connection.request("HEAD", "/", headers={"User-Agent": "sophos-caa-manager/0.1"})
            response = connection.getresponse()
            response.read()
            return 100 <= response.status <= 599
        except OSError:
            return False
        finally:
            connection.close()

    def is_caa_network(self, network: NetworkInfo) -> bool:
        return network.portal_reachable
