"""Tests for bpl.config — YAML configuration loading."""

import textwrap

import pytest

from bpl.config import BplConfig, ConfigError, load_config


class TestBplConfigDefaults:
    """BplConfig should provide sensible defaults for every field."""

    def test_db_path_default(self) -> None:
        cfg = BplConfig()
        assert cfg.db_path.endswith(".bpl/bpl.db")

    def test_maxmind_defaults_are_none(self) -> None:
        cfg = BplConfig()
        assert cfg.maxmind_city_db is None
        assert cfg.maxmind_asn_db is None

    def test_devp2p_binary_default(self) -> None:
        cfg = BplConfig()
        assert cfg.devp2p_binary == "devp2p"

    def test_bsc_node_url_default(self) -> None:
        cfg = BplConfig()
        assert cfg.bsc_node_url == "http://localhost:8545"

    def test_tron_node_url_default(self) -> None:
        cfg = BplConfig()
        assert cfg.tron_node_url == "http://localhost:8090"


class TestLoadConfigExplicitPath:
    """load_config(path=...) with an explicit file path."""

    def test_full_config(self, tmp_path: pytest.TempPathFactory) -> None:
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(
            textwrap.dedent("""\
                db_path: /data/bpl.db
                maxmind_city_db: /data/GeoLite2-City.mmdb
                maxmind_asn_db: /data/GeoLite2-ASN.mmdb
                devp2p_binary: /usr/local/bin/devp2p
                bsc_node_url: http://bsc.example.com:8545
                tron_node_url: http://tron.example.com:8090
            """),
            encoding="utf-8",
        )

        cfg = load_config(cfg_file)

        assert cfg.db_path == "/data/bpl.db"
        assert cfg.maxmind_city_db == "/data/GeoLite2-City.mmdb"
        assert cfg.maxmind_asn_db == "/data/GeoLite2-ASN.mmdb"
        assert cfg.devp2p_binary == "/usr/local/bin/devp2p"
        assert cfg.bsc_node_url == "http://bsc.example.com:8545"
        assert cfg.tron_node_url == "http://tron.example.com:8090"

    def test_partial_config_uses_defaults(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("db_path: /tmp/test.db\n", encoding="utf-8")

        cfg = load_config(cfg_file)

        assert cfg.db_path == "/tmp/test.db"
        # Remaining fields keep their defaults.
        assert cfg.maxmind_city_db is None
        assert cfg.devp2p_binary == "devp2p"
        assert cfg.bsc_node_url == "http://localhost:8545"
        assert cfg.tron_node_url == "http://localhost:8090"

    def test_empty_file_returns_defaults(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("", encoding="utf-8")

        cfg = load_config(cfg_file)

        assert cfg == BplConfig()

    def test_unknown_keys_are_ignored(self, tmp_path: pytest.TempPathFactory) -> None:
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(
            textwrap.dedent("""\
                db_path: /data/bpl.db
                some_future_key: true
                another_unknown: 42
            """),
            encoding="utf-8",
        )

        cfg = load_config(cfg_file)

        assert cfg.db_path == "/data/bpl.db"
        # Unknown keys do not raise; defaults still apply for missing fields.
        assert cfg.maxmind_city_db is None

    def test_accepts_string_path(self, tmp_path: pytest.TempPathFactory) -> None:
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("db_path: /data/bpl.db\n", encoding="utf-8")

        cfg = load_config(str(cfg_file))

        assert cfg.db_path == "/data/bpl.db"


class TestLoadConfigMissingFile:
    """Behavior when the config file doesn't exist."""

    def test_explicit_path_not_found_raises(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        missing = tmp_path / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError, match="Config file not found"):
            load_config(missing)

    def test_no_default_file_returns_defaults(
        self, tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When no path is given and the default doesn't exist, return defaults."""
        import bpl.config as config_mod

        # Point the default path to a location that doesn't exist.
        monkeypatch.setattr(
            config_mod, "DEFAULT_CONFIG_PATH", tmp_path / "nope" / "config.yaml"
        )

        cfg = load_config()

        assert cfg == BplConfig()


class TestLoadConfigInvalidYaml:
    """load_config should raise ConfigError on malformed YAML."""

    def test_invalid_yaml_raises_config_error(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        cfg_file = tmp_path / "bad.yaml"
        cfg_file.write_text(":\n  - :\n    bad: [", encoding="utf-8")

        with pytest.raises(ConfigError, match="Invalid YAML"):
            load_config(cfg_file)

    def test_non_mapping_top_level_raises(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        cfg_file = tmp_path / "list.yaml"
        cfg_file.write_text("- one\n- two\n", encoding="utf-8")

        with pytest.raises(ConfigError, match="Expected a YAML mapping"):
            load_config(cfg_file)
