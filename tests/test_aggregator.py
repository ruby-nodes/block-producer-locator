"""Tests for bpl.aggregator — statistics computation."""

from bpl.aggregator import AggregatedResult, aggregate, aggregate_to_meta
from bpl.models import NodeLocation


def _make_node(**overrides: object) -> NodeLocation:
    """Create a NodeLocation with sensible defaults, overridable per-field."""
    defaults: dict = {
        "ip": "1.2.3.4",
        "port": 30303,
        "network": "test",
        "is_cloud": False,
    }
    defaults.update(overrides)
    return NodeLocation(**defaults)


# ------------------------------------------------------------------
# aggregate()
# ------------------------------------------------------------------


class TestAggregate:
    """Core aggregation logic."""

    def test_empty_list(self) -> None:
        result = aggregate([])
        assert result.country_distribution == []
        assert result.asn_distribution == []
        assert result.cloud_ratio == {"cloud": 0, "bare_metal": 0, "total": 0}

    def test_country_distribution_sorted_desc(self) -> None:
        nodes = [
            _make_node(ip="1.0.0.1", country="Germany"),
            _make_node(ip="1.0.0.2", country="United States"),
            _make_node(ip="1.0.0.3", country="United States"),
            _make_node(ip="1.0.0.4", country="Germany"),
            _make_node(ip="1.0.0.5", country="Germany"),
        ]
        result = aggregate(nodes)
        assert result.country_distribution[0] == ("Germany", 3)
        assert result.country_distribution[1] == ("United States", 2)

    def test_asn_distribution_sorted_desc(self) -> None:
        nodes = [
            _make_node(ip="1.0.0.1", asn=16509, asn_org="Amazon"),
            _make_node(ip="1.0.0.2", asn=16509, asn_org="Amazon"),
            _make_node(ip="1.0.0.3", asn=24940, asn_org="Hetzner"),
        ]
        result = aggregate(nodes)
        assert result.asn_distribution[0] == ("AS16509 / Amazon", 2)
        assert result.asn_distribution[1] == ("AS24940 / Hetzner", 1)

    def test_asn_without_org(self) -> None:
        nodes = [_make_node(asn=12345, asn_org=None)]
        result = aggregate(nodes)
        assert result.asn_distribution == [("AS12345", 1)]

    def test_cloud_vs_bare_metal(self) -> None:
        nodes = [
            _make_node(ip="1.0.0.1", is_cloud=True),
            _make_node(ip="1.0.0.2", is_cloud=True),
            _make_node(ip="1.0.0.3", is_cloud=False),
        ]
        result = aggregate(nodes)
        assert result.cloud_ratio["cloud"] == 2
        assert result.cloud_ratio["bare_metal"] == 1
        assert result.cloud_ratio["total"] == 3

    def test_nodes_without_geo_data(self) -> None:
        """Nodes with None country/asn are excluded from distributions."""
        nodes = [
            _make_node(country=None, asn=None),
            _make_node(country="Germany", asn=24940, asn_org="Hetzner"),
        ]
        result = aggregate(nodes)
        assert result.country_distribution == [("Germany", 1)]
        assert result.asn_distribution == [("AS24940 / Hetzner", 1)]

    def test_returns_aggregated_result(self) -> None:
        result = aggregate([_make_node()])
        assert isinstance(result, AggregatedResult)


# ------------------------------------------------------------------
# aggregate_to_meta()
# ------------------------------------------------------------------


class TestAggregateToMeta:
    """aggregate_to_meta() returns a dict for ProbeResult.meta."""

    def test_returns_expected_keys(self) -> None:
        meta = aggregate_to_meta([_make_node(country="Germany", asn=24940)])
        assert "country_distribution" in meta
        assert "asn_distribution" in meta
        assert "cloud_ratio" in meta

    def test_values_match_aggregate(self) -> None:
        nodes = [
            _make_node(ip="1.0.0.1", country="Germany", is_cloud=True),
            _make_node(ip="1.0.0.2", country="Germany", is_cloud=False),
        ]
        meta = aggregate_to_meta(nodes)
        agg = aggregate(nodes)
        assert meta["country_distribution"] == agg.country_distribution
        assert meta["cloud_ratio"] == agg.cloud_ratio

    def test_empty_list_returns_zeroed_ratio(self) -> None:
        meta = aggregate_to_meta([])
        assert meta["cloud_ratio"]["total"] == 0
