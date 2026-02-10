"""Tests for the CLI entry point."""

from click.testing import CliRunner

from bpl.cli import main


class TestCliHelp:
    """--help flag produces usage information."""

    def test_help_exits_zero(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Locate block-producing nodes" in result.output

    def test_help_shows_network_option(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert "--network" in result.output

    def test_help_shows_format_option(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert "--format" in result.output

    def test_help_shows_config_option(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert "--config" in result.output


class TestNetworkOption:
    """--network flag validation."""

    def test_valid_network_accepted(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--network", "base"])
        assert result.exit_code == 0
        assert "network=base" in result.output

    def test_all_network_accepted(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--network", "all"])
        assert result.exit_code == 0
        assert "network=all" in result.output

    def test_invalid_network_rejected(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--network", "invalid"])
        assert result.exit_code != 0
        assert "Invalid value" in result.output

    def test_network_is_required(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, [])
        assert result.exit_code != 0
        assert "Missing option" in result.output

    def test_network_case_insensitive(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--network", "BSC"])
        assert result.exit_code == 0
        assert "network=bsc" in result.output

    def test_short_flag(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["-n", "tron"])
        assert result.exit_code == 0
        assert "network=tron" in result.output


class TestFormatOption:
    """--format flag validation."""

    def test_default_is_table(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--network", "base"])
        assert result.exit_code == 0
        assert "format=table" in result.output

    def test_json_format(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--network", "base", "--format", "json"])
        assert result.exit_code == 0
        assert "format=json" in result.output

    def test_invalid_format_rejected(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--network", "base", "--format", "xml"])
        assert result.exit_code != 0
        assert "Invalid value" in result.output

    def test_short_flag(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["-n", "base", "-f", "json"])
        assert result.exit_code == 0
        assert "format=json" in result.output


class TestConfigOption:
    """--config flag validation."""

    def test_missing_config_file_errors(self, tmp_path) -> None:
        runner = CliRunner()
        missing = str(tmp_path / "nonexistent.yaml")
        result = runner.invoke(main, ["--network", "base", "--config", missing])
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_valid_config_file_loaded(self, tmp_path) -> None:
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("db_path: /tmp/test.db\n")
        runner = CliRunner()
        result = runner.invoke(main, ["--network", "base", "--config", str(cfg_file)])
        assert result.exit_code == 0

    def test_invalid_yaml_errors(self, tmp_path) -> None:
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(": : : bad yaml\n")
        runner = CliRunner()
        result = runner.invoke(main, ["--network", "base", "--config", str(cfg_file)])
        assert result.exit_code == 1
        assert "Error" in result.output

    def test_default_config_not_required(self, tmp_path, monkeypatch) -> None:
        """CLI works fine when no config file exists at all."""
        monkeypatch.setattr("bpl.config.DEFAULT_CONFIG_PATH", tmp_path / "nope.yaml")
        runner = CliRunner()
        result = runner.invoke(main, ["--network", "base"])
        assert result.exit_code == 0
