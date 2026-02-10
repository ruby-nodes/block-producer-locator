"""Tests for the output renderer."""

import json

import pytest

from bpl.models import NodeLocation, ProbeResult
from bpl.output import render, render_to_string

# -- Fixtures ----------------------------------------------------------------


def _make_node(**overrides: object) -> NodeLocation:
    """Create a ``NodeLocation`` with sensible defaults, overridable."""
    defaults: dict = {
        "ip": "1.2.3.4",
        "port": 30303,
        "network": "test",
    }
    defaults.update(overrides)
    return NodeLocation(**defaults)


def _single_result() -> ProbeResult:
    """ProbeResult with mode='single' and one enriched node."""
    node = _make_node(
        ip="93.184.216.34",
        port=443,
        network="base",
        city="Los Angeles",
        country="United States",
        country_code="US",
        asn=15133,
        asn_org="Edgecast Inc.",
        cloud_provider="AWS",
        cloud_region="us-west-2",
        is_cloud=True,
    )
    return ProbeResult(network="base", mode="single", nodes=[node])


def _list_result() -> ProbeResult:
    """ProbeResult with mode='list' and several nodes."""
    nodes = [
        _make_node(
            ip="10.0.0.1",
            port=30303,
            network="bsc",
            role="validator",
            label="Validator A",
            country="Germany",
            asn_org="Hetzner",
            cloud_provider=None,
            is_cloud=False,
        ),
        _make_node(
            ip="10.0.0.2",
            port=30303,
            network="bsc",
            role="validator",
            label="Validator B",
            country="United States",
            asn_org="AWS",
            cloud_provider="AWS",
            is_cloud=True,
        ),
        _make_node(
            ip="10.0.0.3",
            port=30303,
            network="bsc",
            role="validator",
            label="Validator C",
            country="United States",
            asn_org="AWS",
            cloud_provider="AWS",
            is_cloud=True,
        ),
    ]
    return ProbeResult(network="bsc", mode="list", nodes=nodes)


def _aggregate_result() -> ProbeResult:
    """ProbeResult with mode='aggregate' and stats in meta."""
    return ProbeResult(
        network="ethereum",
        mode="aggregate",
        nodes=[],
        meta={
            "country_distribution": [
                ("United States", 120),
                ("Germany", 80),
                ("Singapore", 30),
            ],
            "asn_distribution": [
                ("AS16509 / Amazon", 90),
                ("AS24940 / Hetzner", 60),
            ],
            "cloud_ratio": {
                "cloud": 150,
                "bare_metal": 80,
                "total": 230,
            },
        },
    )


# -- render() dispatch -------------------------------------------------------


class TestRenderDispatch:
    """render() routes to the correct formatter."""

    def test_unknown_format_raises(self) -> None:
        result = _single_result()
        with pytest.raises(ValueError, match="Unknown output format"):
            render(result, "xml")

    def test_table_format_produces_output(self) -> None:
        output = render_to_string(_single_result(), "table")
        assert len(output) > 0

    def test_json_format_produces_valid_json(self) -> None:
        output = render_to_string(_single_result(), "json")
        parsed = json.loads(output)
        assert isinstance(parsed, dict)


# -- Single mode (table) -----------------------------------------------------


class TestSingleTable:
    """Table output for mode='single'."""

    def test_contains_network_header(self) -> None:
        output = render_to_string(_single_result(), "table")
        assert "base" in output
        assert "sequencer" in output

    def test_contains_ip(self) -> None:
        output = render_to_string(_single_result(), "table")
        assert "93.184.216.34" in output

    def test_contains_geo_fields(self) -> None:
        output = render_to_string(_single_result(), "table")
        assert "Los Angeles" in output
        assert "United States" in output

    def test_contains_cloud_fields(self) -> None:
        output = render_to_string(_single_result(), "table")
        assert "AWS" in output
        assert "us-west-2" in output


# -- List mode (table) -------------------------------------------------------


class TestListTable:
    """Table output for mode='list'."""

    def test_contains_node_count_in_title(self) -> None:
        output = render_to_string(_list_result(), "table")
        assert "3 nodes" in output

    def test_contains_all_ips(self) -> None:
        output = render_to_string(_list_result(), "table")
        assert "10.0.0.1" in output
        assert "10.0.0.2" in output
        assert "10.0.0.3" in output

    def test_contains_roles_and_labels(self) -> None:
        output = render_to_string(_list_result(), "table")
        assert "validator" in output
        assert "Validator A" in output

    def test_summary_line_present(self) -> None:
        output = render_to_string(_list_result(), "table")
        # 2 of 3 are cloud => 67%
        assert "3 nodes" in output
        assert "2 cloud" in output
        assert "67%" in output

    def test_summary_shows_top_country(self) -> None:
        output = render_to_string(_list_result(), "table")
        assert "United States" in output

    def test_none_fields_show_dash(self) -> None:
        result = ProbeResult(
            network="test",
            mode="list",
            nodes=[_make_node(role=None, label=None, cloud_provider=None)],
        )
        output = render_to_string(result, "table")
        assert "—" in output


# -- Aggregate mode (table) --------------------------------------------------


class TestAggregateTable:
    """Table output for mode='aggregate'."""

    def test_contains_network_heading(self) -> None:
        output = render_to_string(_aggregate_result(), "table")
        assert "ethereum" in output
        assert "aggregate" in output.lower()

    def test_contains_country_distribution(self) -> None:
        output = render_to_string(_aggregate_result(), "table")
        assert "United States" in output
        assert "120" in output
        assert "Germany" in output

    def test_contains_asn_distribution(self) -> None:
        output = render_to_string(_aggregate_result(), "table")
        assert "Amazon" in output
        assert "90" in output

    def test_contains_cloud_ratio(self) -> None:
        output = render_to_string(_aggregate_result(), "table")
        assert "150" in output  # cloud count
        assert "80" in output  # bare-metal count

    def test_empty_meta_shows_no_data_message(self) -> None:
        result = ProbeResult(network="ethereum", mode="aggregate", nodes=[])
        output = render_to_string(result, "table")
        assert "No aggregate data available" in output


# -- Single mode (JSON) ------------------------------------------------------


class TestSingleJson:
    """JSON output for mode='single'."""

    def test_valid_json_with_expected_keys(self) -> None:
        output = render_to_string(_single_result(), "json")
        data = json.loads(output)
        assert data["network"] == "base"
        assert data["mode"] == "single"
        assert isinstance(data["nodes"], list)
        assert len(data["nodes"]) == 1

    def test_node_contains_ip_and_geo(self) -> None:
        output = render_to_string(_single_result(), "json")
        node = json.loads(output)["nodes"][0]
        assert node["ip"] == "93.184.216.34"
        assert node["city"] == "Los Angeles"
        assert node["country"] == "United States"
        assert node["cloud_provider"] == "AWS"


# -- List mode (JSON) --------------------------------------------------------


class TestListJson:
    """JSON output for mode='list'."""

    def test_all_nodes_present(self) -> None:
        output = render_to_string(_list_result(), "json")
        data = json.loads(output)
        assert len(data["nodes"]) == 3

    def test_node_fields(self) -> None:
        output = render_to_string(_list_result(), "json")
        node = json.loads(output)["nodes"][0]
        assert node["role"] == "validator"
        assert node["label"] == "Validator A"


# -- Aggregate mode (JSON) ---------------------------------------------------


class TestAggregateJson:
    """JSON output for mode='aggregate'."""

    def test_meta_contains_stats(self) -> None:
        output = render_to_string(_aggregate_result(), "json")
        data = json.loads(output)
        assert data["mode"] == "aggregate"
        assert "country_distribution" in data["meta"]
        assert "asn_distribution" in data["meta"]
        assert "cloud_ratio" in data["meta"]

    def test_country_distribution_values(self) -> None:
        output = render_to_string(_aggregate_result(), "json")
        meta = json.loads(output)["meta"]
        countries = dict(meta["country_distribution"])
        assert countries["United States"] == 120
        assert countries["Germany"] == 80
