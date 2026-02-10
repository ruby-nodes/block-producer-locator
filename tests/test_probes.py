"""Tests for the probe registry and abstract Probe base class."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from bpl.cli import main
from bpl.config import BplConfig
from bpl.probes import Probe, get_probe, registered_networks
from bpl.probes.base_l2 import BaseL2Probe
from bpl.probes.bsc import BSCProbe
from bpl.probes.ethereum import EthereumProbe
from bpl.probes.optimism import OptimismProbe
from bpl.probes.starknet import StarknetProbe
from bpl.probes.tron import TRONProbe


class TestProbeABC:
    """Probe is abstract and cannot be instantiated directly."""

    def test_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError, match="abstract method"):
            Probe()  # type: ignore[abstract]

    def test_subclass_must_implement_run(self) -> None:
        class Incomplete(Probe):
            pass

        with pytest.raises(TypeError, match="abstract method"):
            Incomplete()  # type: ignore[abstract]

    def test_complete_subclass_instantiates(self) -> None:
        class Complete(Probe):
            def run(self, config):
                return None  # type: ignore[return-value]

        probe = Complete()
        assert isinstance(probe, Probe)


class TestGetProbe:
    """get_probe() returns the correct class for each network."""

    @pytest.mark.parametrize(
        ("network", "expected_cls"),
        [
            ("base", BaseL2Probe),
            ("optimism", OptimismProbe),
            ("starknet", StarknetProbe),
            ("bsc", BSCProbe),
            ("tron", TRONProbe),
            ("ethereum", EthereumProbe),
        ],
    )
    def test_returns_correct_class(
        self, network: str, expected_cls: type[Probe]
    ) -> None:
        probe = get_probe(network)
        assert isinstance(probe, expected_cls)

    def test_unknown_network_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown network 'fakenet'"):
            get_probe("fakenet")

    def test_error_lists_known_networks(self) -> None:
        with pytest.raises(ValueError, match="base") as exc_info:
            get_probe("fakenet")
        msg = str(exc_info.value)
        for net in ("base", "bsc", "ethereum", "optimism", "starknet", "tron"):
            assert net in msg


class TestRegisteredNetworks:
    """registered_networks() returns sorted network names."""

    def test_returns_all_six(self) -> None:
        nets = registered_networks()
        assert len(nets) == 6

    def test_sorted(self) -> None:
        nets = registered_networks()
        assert nets == sorted(nets)

    def test_known_networks_present(self) -> None:
        nets = registered_networks()
        for expected in ("base", "bsc", "ethereum", "optimism", "starknet", "tron"):
            assert expected in nets


class TestStubProbes:
    """All stubs raise NotImplementedError."""

    @pytest.mark.parametrize(
        "network",
        ["optimism", "starknet", "bsc", "tron", "ethereum"],
    )
    def test_stub_raises_not_implemented(self, network: str) -> None:
        probe = get_probe(network)
        cfg = BplConfig()
        with pytest.raises(NotImplementedError):
            probe.run(cfg)


class TestBaseL2Probe:
    """BaseL2Probe resolves DNS and returns a ProbeResult."""

    @patch("bpl.probes.base_l2.resolve_all")
    def test_returns_single_mode(self, mock_resolve: MagicMock) -> None:
        mock_resolve.return_value = [("1.2.3.4", 0)]
        probe = BaseL2Probe()
        result = probe.run(BplConfig())
        assert result.mode == "single"
        assert result.network == "base"

    @patch("bpl.probes.base_l2.resolve_all")
    def test_node_fields(self, mock_resolve: MagicMock) -> None:
        mock_resolve.return_value = [("10.0.0.1", 443)]
        result = BaseL2Probe().run(BplConfig())
        assert len(result.nodes) == 1
        node = result.nodes[0]
        assert node.ip == "10.0.0.1"
        assert node.port == 443
        assert node.network == "base"
        assert node.role == "sequencer"

    @patch("bpl.probes.base_l2.resolve_all")
    def test_multiple_addresses(self, mock_resolve: MagicMock) -> None:
        mock_resolve.return_value = [
            ("1.2.3.4", 0),
            ("5.6.7.8", 0),
            ("2001:db8::1", 0),
        ]
        result = BaseL2Probe().run(BplConfig())
        assert len(result.nodes) == 3
        ips = [n.ip for n in result.nodes]
        assert ips == ["1.2.3.4", "5.6.7.8", "2001:db8::1"]

    @patch("bpl.probes.base_l2.resolve_all")
    def test_calls_resolve_with_correct_host(self, mock_resolve: MagicMock) -> None:
        mock_resolve.return_value = []
        BaseL2Probe().run(BplConfig())
        mock_resolve.assert_called_once_with("mainnet-sequencer.base.org")

    @patch("bpl.probes.base_l2.resolve_all")
    def test_empty_dns_result(self, mock_resolve: MagicMock) -> None:
        mock_resolve.return_value = []
        result = BaseL2Probe().run(BplConfig())
        assert result.nodes == []
        assert result.mode == "single"


class TestCLIProbeDispatch:
    """CLI dispatches to probes and handles NotImplementedError gracefully."""

    @patch("bpl.probes.base_l2.resolve_all", return_value=[("1.2.3.4", 0)])
    def test_single_network_dispatch(self, _mock_resolve: MagicMock) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--network", "base"])
        assert result.exit_code == 0
        # Base probe is now implemented — output should contain the IP
        assert "1.2.3.4" in result.output

    @patch("bpl.probes.base_l2.resolve_all", return_value=[("1.2.3.4", 0)])
    def test_all_networks_dispatch(self, _mock_resolve: MagicMock) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--network", "all"])
        assert result.exit_code == 0
        # Base should show the resolved IP; stubs should say not yet implemented
        assert "1.2.3.4" in result.output
        for net in ("optimism", "starknet", "bsc", "tron", "ethereum"):
            assert f"network={net}" in result.output
