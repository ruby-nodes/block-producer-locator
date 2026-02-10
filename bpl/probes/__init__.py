"""Probe registry and abstract Probe base class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bpl.config import BplConfig
    from bpl.models import ProbeResult


class Probe(ABC):
    """Abstract base class for all network probes.

    Each supported blockchain network implements a concrete subclass
    that knows how to discover nodes on that network.
    """

    @abstractmethod
    def run(self, config: BplConfig) -> ProbeResult:
        """Execute the probe and return results.

        Args:
            config: Loaded application configuration.

        Returns:
            A ``ProbeResult`` with discovered nodes.
        """


def _build_registry() -> dict[str, type[Probe]]:
    """Build the network-name → Probe-class mapping.

    Imports are deferred to avoid circular imports and to keep the
    registry definition in one place.
    """
    from bpl.probes.base_l2 import BaseL2Probe
    from bpl.probes.bsc import BSCProbe
    from bpl.probes.ethereum import EthereumProbe
    from bpl.probes.optimism import OptimismProbe
    from bpl.probes.starknet import StarknetProbe
    from bpl.probes.tron import TRONProbe

    return {
        "base": BaseL2Probe,
        "optimism": OptimismProbe,
        "starknet": StarknetProbe,
        "bsc": BSCProbe,
        "tron": TRONProbe,
        "ethereum": EthereumProbe,
    }


def get_probe(network: str) -> Probe:
    """Look up and instantiate the probe for *network*.

    Args:
        network: Network name (e.g. ``"base"``, ``"bsc"``).

    Returns:
        An instance of the matching ``Probe`` subclass.

    Raises:
        ValueError: If *network* is not in the registry.
    """
    registry = _build_registry()
    probe_cls = registry.get(network)
    if probe_cls is None:
        known = ", ".join(sorted(registry))
        raise ValueError(f"Unknown network {network!r}. Known networks: {known}")
    return probe_cls()


def registered_networks() -> list[str]:
    """Return a sorted list of all registered network names."""
    return sorted(_build_registry())
