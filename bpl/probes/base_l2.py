"""Base L2 sequencer probe (DNS-based)."""

import logging

from bpl.config import BplConfig
from bpl.dns import resolve_all
from bpl.models import NodeLocation, ProbeResult
from bpl.probes import Probe

logger = logging.getLogger(__name__)

SEQUENCER_HOST = "mainnet-sequencer.base.org"


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
        logger.info("Resolving %s", SEQUENCER_HOST)
        addresses = resolve_all(SEQUENCER_HOST)

        nodes = [
            NodeLocation(
                ip=ip,
                port=port,
                network="base",
                role="sequencer",
            )
            for ip, port in addresses
        ]

        logger.info("Discovered %d address(es) for %s", len(nodes), SEQUENCER_HOST)
        return ProbeResult(network="base", mode="single", nodes=nodes)
