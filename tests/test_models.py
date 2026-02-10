"""Tests for bpl.models dataclasses."""

from datetime import UTC, datetime

from bpl.models import CrawlRun, NodeLocation, ProbeResult


class TestNodeLocation:
    """Tests for the NodeLocation dataclass."""

    def test_minimal_construction(self) -> None:
        """Only required fields are needed; optional fields default to None."""
        node = NodeLocation(ip="1.2.3.4", port=30303, network="bsc")

        assert node.ip == "1.2.3.4"
        assert node.port == 30303
        assert node.network == "bsc"
        assert node.node_id is None
        assert node.role is None
        assert node.label is None

    def test_geo_fields_default_to_none(self) -> None:
        """Geo-enrichment fields are None before enrichment."""
        node = NodeLocation(ip="10.0.0.1", port=8545, network="ethereum")

        assert node.city is None
        assert node.country is None
        assert node.country_code is None
        assert node.latitude is None
        assert node.longitude is None
        assert node.asn is None
        assert node.asn_org is None
        assert node.cloud_provider is None
        assert node.cloud_region is None
        assert node.is_cloud is None

    def test_raw_data_defaults_to_empty_dict(self) -> None:
        """raw_data defaults to a fresh empty dict per instance."""
        node_a = NodeLocation(ip="1.1.1.1", port=80, network="base")
        node_b = NodeLocation(ip="2.2.2.2", port=80, network="base")

        assert node_a.raw_data == {}
        assert node_b.raw_data == {}
        # Ensure they are distinct objects (no shared mutable default).
        assert node_a.raw_data is not node_b.raw_data

    def test_full_construction(self) -> None:
        """All fields can be set explicitly."""
        node = NodeLocation(
            ip="34.56.78.90",
            port=30303,
            network="bsc",
            node_id="abc123",
            role="validator",
            label="Validator-1",
            city="Frankfurt",
            country="Germany",
            country_code="DE",
            latitude=50.1109,
            longitude=8.6821,
            asn=16509,
            asn_org="Amazon.com, Inc.",
            cloud_provider="AWS",
            cloud_region="eu-central-1",
            is_cloud=True,
            raw_data={"client": "geth/v1.3.0"},
        )

        assert node.role == "validator"
        assert node.country_code == "DE"
        assert node.is_cloud is True
        assert node.raw_data == {"client": "geth/v1.3.0"}


class TestProbeResult:
    """Tests for the ProbeResult dataclass."""

    def test_construction_with_nodes(self) -> None:
        """ProbeResult holds a list of NodeLocation objects."""
        nodes = [
            NodeLocation(ip="1.2.3.4", port=30303, network="bsc"),
            NodeLocation(ip="5.6.7.8", port=30303, network="bsc"),
        ]
        result = ProbeResult(network="bsc", mode="list", nodes=nodes)

        assert result.network == "bsc"
        assert result.mode == "list"
        assert len(result.nodes) == 2
        assert result.nodes[0].ip == "1.2.3.4"

    def test_meta_defaults_to_empty_dict(self) -> None:
        """meta defaults to a fresh empty dict per instance."""
        r1 = ProbeResult(network="base", mode="single", nodes=[])
        r2 = ProbeResult(network="base", mode="single", nodes=[])

        assert r1.meta == {}
        assert r1.meta is not r2.meta

    def test_single_mode(self) -> None:
        """Single mode is valid for L2 sequencer probes."""
        node = NodeLocation(ip="10.0.0.1", port=443, network="optimism")
        result = ProbeResult(network="optimism", mode="single", nodes=[node])

        assert result.mode == "single"
        assert len(result.nodes) == 1

    def test_aggregate_mode(self) -> None:
        """Aggregate mode is valid for Ethereum probes."""
        result = ProbeResult(
            network="ethereum",
            mode="aggregate",
            nodes=[],
            meta={"total_crawled": 10000},
        )

        assert result.mode == "aggregate"
        assert result.meta["total_crawled"] == 10000


class TestCrawlRun:
    """Tests for the CrawlRun dataclass."""

    def test_minimal_construction(self) -> None:
        """Required fields only; id is None, timestamp is auto-generated."""
        run = CrawlRun(network="bsc", node_count=21, duration_seconds=12.5)

        assert run.network == "bsc"
        assert run.node_count == 21
        assert run.duration_seconds == 12.5
        assert run.id is None

    def test_timestamp_defaults_to_utc_now(self) -> None:
        """Timestamp is automatically set to approximately now (UTC)."""
        before = datetime.now(UTC)
        run = CrawlRun(network="tron", node_count=27, duration_seconds=3.0)
        after = datetime.now(UTC)

        assert run.timestamp.tzinfo == UTC
        assert before <= run.timestamp <= after

    def test_meta_defaults_to_empty_dict(self) -> None:
        """meta defaults to a fresh empty dict per instance."""
        r1 = CrawlRun(network="base", node_count=1, duration_seconds=0.5)
        r2 = CrawlRun(network="base", node_count=1, duration_seconds=0.5)

        assert r1.meta == {}
        assert r1.meta is not r2.meta

    def test_full_construction(self) -> None:
        """All fields can be set explicitly."""
        ts = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
        run = CrawlRun(
            network="ethereum",
            node_count=9500,
            duration_seconds=120.0,
            id="abc-123-uuid",
            timestamp=ts,
            meta={"bootnodes_used": 4},
        )

        assert run.id == "abc-123-uuid"
        assert run.timestamp == ts
        assert run.meta["bootnodes_used"] == 4
