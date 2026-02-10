"""BSC probe: devp2p crawl + admin_peers + on-chain validator set."""

from bpl.config import BplConfig
from bpl.models import ProbeResult
from bpl.probes import Probe


class BSCProbe(Probe):
    """Probe for BSC (BNB Smart Chain) validators.

    Combines ``devp2p discv4 crawl``, ``admin_peers`` JSON-RPC, and
    on-chain validator set queries to identify active validators.
    """

    def run(self, config: BplConfig) -> ProbeResult:
        """Execute the BSC validator probe.

        Args:
            config: Loaded application configuration.

        Returns:
            A ``ProbeResult`` with mode ``"list"``.
        """
        raise NotImplementedError("BSCProbe is not yet implemented")
