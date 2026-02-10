"""Optimism sequencer probe (DNS-based)."""

from bpl.config import BplConfig
from bpl.models import ProbeResult
from bpl.probes import Probe


class OptimismProbe(Probe):
    """Probe for the Optimism L2 sequencer.

    Resolves ``mainnet-sequencer.optimism.io`` via DNS to locate the
    sequencer endpoint.
    """

    def run(self, config: BplConfig) -> ProbeResult:
        """Execute the Optimism sequencer probe.

        Args:
            config: Loaded application configuration.

        Returns:
            A ``ProbeResult`` with mode ``"single"``.
        """
        raise NotImplementedError("OptimismProbe is not yet implemented")
