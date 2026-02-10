"""Data models: NodeLocation, ProbeResult, CrawlRun dataclasses."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal


@dataclass
class NodeLocation:
    """A discovered node with optional geo-enrichment fields.

    Probes populate the discovery fields (ip, port, network, etc.).
    The geo-IP pipeline fills in the geographic and cloud fields later.

    Attributes:
        ip: IPv4 or IPv6 address of the node.
        port: Listening port.
        network: Network name (e.g. "base", "bsc", "ethereum").
        node_id: Protocol-level node identifier (enode, peer ID), if known.
        role: Node role such as "validator", "sequencer", or None.
        label: Human-readable label (e.g. validator moniker).
        city: City name from GeoLite2-City.
        country: Country name from GeoLite2-City.
        country_code: ISO 3166-1 alpha-2 country code.
        latitude: Latitude from GeoLite2-City.
        longitude: Longitude from GeoLite2-City.
        asn: Autonomous System Number from GeoLite2-ASN.
        asn_org: AS organization name from GeoLite2-ASN.
        cloud_provider: Cloud provider name (e.g. "AWS", "GCP"), if detected.
        cloud_region: Inferred cloud region (e.g. "us-east-1"), if detected.
        is_cloud: Whether the IP belongs to a known cloud provider.
        raw_data: Arbitrary network-specific metadata (enode, client version,
            vote count, etc.).
    """

    # -- Discovery fields (set by probes) --
    ip: str
    port: int
    network: str
    node_id: str | None = None
    role: str | None = None
    label: str | None = None

    # -- Geo-enrichment fields (set by geoip.enrich) --
    city: str | None = None
    country: str | None = None
    country_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    asn: int | None = None
    asn_org: str | None = None
    cloud_provider: str | None = None
    cloud_region: str | None = None
    is_cloud: bool | None = None

    # -- Extra metadata --
    raw_data: dict = field(default_factory=dict)


@dataclass
class ProbeResult:
    """Result returned by every probe's ``run()`` method.

    Attributes:
        network: Network name (e.g. "base", "bsc").
        mode: Output mode — "single" for L2 sequencers, "list" for validator
            sets, "aggregate" for large crawls.
        nodes: Discovered nodes.
        meta: Optional extra information about the probe run.
    """

    network: str
    mode: Literal["single", "list", "aggregate"]
    nodes: list[NodeLocation]
    meta: dict = field(default_factory=dict)


@dataclass
class CrawlRun:
    """Audit record for a single probe execution.

    Attributes:
        network: Network that was probed.
        node_count: Number of nodes discovered.
        duration_seconds: Wall-clock duration of the probe run.
        id: UUID assigned at persist time; None until persisted.
        timestamp: When the crawl started (UTC).
        meta: Optional extra information about the run.
    """

    network: str
    node_count: int
    duration_seconds: float
    id: str | None = None
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )
    meta: dict = field(default_factory=dict)
