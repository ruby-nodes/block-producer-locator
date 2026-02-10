"""Starknet sequencer probe (DNS-based)."""

from bpl.config import BplConfig
from bpl.models import ProbeResult
from bpl.probes import Probe


class StarknetProbe(Probe):
    """Probe for the Starknet sequencer.

    Resolves ``alpha-mainnet.starknet.io`` via DNS to locate the
    sequencer endpoint.
    """

    def run(self, config: BplConfig) -> ProbeResult:
        """Execute the Starknet sequencer probe.

        Args:
            config: Loaded application configuration.

        Returns:
            A ``ProbeResult`` with mode ``"single"``.
        """
        raise NotImplementedError("StarknetProbe is not yet implemented")
