"""Aggregator: country distribution, ASN breakdown, cloud-vs-bare-metal ratio."""

import logging
from dataclasses import dataclass, field

from bpl.models import NodeLocation

logger = logging.getLogger(__name__)


@dataclass
class AggregatedResult:
    """Aggregated statistics computed from a list of nodes.

    Attributes:
        country_distribution: ``(country_name, count)`` pairs sorted by
            count descending.
        asn_distribution: ``("ASNNNN / org", count)`` pairs sorted by
            count descending.
        cloud_ratio: Dict with keys ``cloud``, ``bare_metal``, ``total``.
    """

    country_distribution: list[tuple[str, int]] = field(default_factory=list)
    asn_distribution: list[tuple[str, int]] = field(default_factory=list)
    cloud_ratio: dict[str, int] = field(default_factory=dict)


def aggregate(nodes: list[NodeLocation]) -> AggregatedResult:
    """Compute aggregate statistics from a list of enriched nodes.

    Args:
        nodes: Node locations with geo-enrichment fields populated.

    Returns:
        An ``AggregatedResult`` with country distribution, ASN
        distribution, and cloud-vs-bare-metal ratio.
    """
    country_counts: dict[str, int] = {}
    asn_counts: dict[str, int] = {}
    cloud = 0
    bare_metal = 0

    for node in nodes:
        # Country distribution
        if node.country:
            country_counts[node.country] = country_counts.get(node.country, 0) + 1

        # ASN distribution
        if node.asn is not None:
            label = f"AS{node.asn}"
            if node.asn_org:
                label = f"{label} / {node.asn_org}"
            asn_counts[label] = asn_counts.get(label, 0) + 1

        # Cloud vs bare-metal
        if node.is_cloud:
            cloud += 1
        else:
            bare_metal += 1

    country_distribution = sorted(
        country_counts.items(), key=lambda item: item[1], reverse=True
    )
    asn_distribution = sorted(
        asn_counts.items(), key=lambda item: item[1], reverse=True
    )
    cloud_ratio = {
        "cloud": cloud,
        "bare_metal": bare_metal,
        "total": len(nodes),
    }

    return AggregatedResult(
        country_distribution=country_distribution,
        asn_distribution=asn_distribution,
        cloud_ratio=cloud_ratio,
    )


def aggregate_to_meta(nodes: list[NodeLocation]) -> dict:
    """Compute aggregate statistics and return as a plain dict.

    This is a convenience wrapper around ``aggregate()`` that returns
    the result in the format expected by ``output.render_table_aggregate``
    (i.e. suitable for ``ProbeResult.meta``).

    Args:
        nodes: Node locations with geo-enrichment fields populated.

    Returns:
        A dict with keys ``country_distribution``, ``asn_distribution``,
        and ``cloud_ratio``.
    """
    result = aggregate(nodes)
    return {
        "country_distribution": result.country_distribution,
        "asn_distribution": result.asn_distribution,
        "cloud_ratio": result.cloud_ratio,
    }
