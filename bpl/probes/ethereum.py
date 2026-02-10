"""Ethereum probe: devp2p DHT crawl, aggregate statistics only."""

from bpl.config import BplConfig
from bpl.models import ProbeResult
from bpl.probes import Probe


class EthereumProbe(Probe):
    """Probe for Ethereum mainnet nodes.

    Runs a ``devp2p discv4 crawl`` with Ethereum mainnet bootnodes
    and produces aggregate-only statistics (no individual validator
    identification).
    """

    def run(self, config: BplConfig) -> ProbeResult:
        """Execute the Ethereum DHT crawl probe.

        Args:
            config: Loaded application configuration.

        Returns:
            A ``ProbeResult`` with mode ``"aggregate"``.
        """
        raise NotImplementedError("EthereumProbe is not yet implemented")
