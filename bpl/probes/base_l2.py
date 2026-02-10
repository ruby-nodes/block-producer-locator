"""Base L2 sequencer probe (DNS-based)."""

from bpl.config import BplConfig
from bpl.models import ProbeResult
from bpl.probes import Probe


class BaseL2Probe(Probe):
    """Probe for the Base L2 sequencer.

    Resolves ``mainnet-sequencer.base.org`` via DNS to locate the
    sequencer endpoint.
    """

    def run(self, config: BplConfig) -> ProbeResult:
        """Execute the Base sequencer probe.

        Args:
            config: Loaded application configuration.

        Returns:
            A ``ProbeResult`` with mode ``"single"``.
        """
        raise NotImplementedError("BaseL2Probe is not yet implemented")
