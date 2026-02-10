"""TRON probe: java-tron HTTP API (listnodes + listwitnesses)."""

from bpl.config import BplConfig
from bpl.models import ProbeResult
from bpl.probes import Probe


class TRONProbe(Probe):
    """Probe for TRON Super Representatives.

    Uses java-tron HTTP API (``wallet/listnodes`` and
    ``wallet/listwitnesses``) to discover nodes and correlate
    Super Representative addresses to peer IPs.
    """

    def run(self, config: BplConfig) -> ProbeResult:
        """Execute the TRON probe.

        Args:
            config: Loaded application configuration.

        Returns:
            A ``ProbeResult`` with mode ``"list"``.
        """
        raise NotImplementedError("TRONProbe is not yet implemented")
