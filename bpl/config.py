"""YAML configuration file loading."""

import logging
from dataclasses import dataclass
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_DIR = Path.home() / ".bpl"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.yaml"
DEFAULT_DB_PATH = str(DEFAULT_CONFIG_DIR / "bpl.db")


@dataclass
class BplConfig:
    """Top-level configuration for the bpl tool.

    All fields have sensible defaults so the tool works out of the box
    for simple use cases (e.g. L2 sequencer probes that need no external
    endpoints).

    Attributes:
        db_path: Path to the SQLite database file.
        maxmind_city_db: Path to GeoLite2-City.mmdb, or None if not configured.
        maxmind_asn_db: Path to GeoLite2-ASN.mmdb, or None if not configured.
        devp2p_binary: Path (or bare name for $PATH lookup) of the devp2p
            Go binary used for DHT crawling.
        bsc_node_url: JSON-RPC endpoint for a BSC geth node.
        tron_node_url: HTTP API endpoint for a java-tron node.
    """

    db_path: str = DEFAULT_DB_PATH
    maxmind_city_db: str | None = None
    maxmind_asn_db: str | None = None
    devp2p_binary: str = "devp2p"
    bsc_node_url: str = "http://localhost:8545"
    tron_node_url: str = "http://localhost:8090"


# Keys in the YAML file that map to BplConfig fields.
_YAML_KEY_TO_FIELD: dict[str, str] = {
    "db_path": "db_path",
    "maxmind_city_db": "maxmind_city_db",
    "maxmind_asn_db": "maxmind_asn_db",
    "devp2p_binary": "devp2p_binary",
    "bsc_node_url": "bsc_node_url",
    "tron_node_url": "tron_node_url",
}


def load_config(path: Path | str | None = None) -> BplConfig:
    """Load configuration from a YAML file.

    Args:
        path: Explicit path to a YAML config file.  If ``None``, the
            default location (``~/.bpl/config.yaml``) is tried.  If the
            default file doesn't exist, a ``BplConfig`` with all defaults
            is returned silently.

    Returns:
        A populated ``BplConfig`` instance.

    Raises:
        FileNotFoundError: If an explicit *path* was given but doesn't exist.
        ConfigError: If the file contains invalid YAML or has an unexpected
            top-level structure.
    """
    resolved = _resolve_path(path)

    if resolved is None:
        logger.debug("No config file found; using defaults")
        return BplConfig()

    logger.debug("Loading config from %s", resolved)
    text = resolved.read_text(encoding="utf-8")

    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {resolved}: {exc}") from exc

    if raw is None:
        # Empty file — treat as all-defaults.
        return BplConfig()

    if not isinstance(raw, dict):
        raise ConfigError(
            f"Expected a YAML mapping at the top level in {resolved}, "
            f"got {type(raw).__name__}"
        )

    return _build_config(raw, source=resolved)


class ConfigError(Exception):
    """Raised when a configuration file is malformed or unreadable."""


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _resolve_path(path: Path | str | None) -> Path | None:
    """Return a concrete ``Path`` to read, or ``None`` if nothing to read.

    Raises:
        FileNotFoundError: If the caller supplied an explicit path that
            doesn't exist on disk.
    """
    if path is not None:
        p = Path(path).expanduser()
        if not p.is_file():
            raise FileNotFoundError(f"Config file not found: {p}")
        return p

    # Try the default location.
    default = DEFAULT_CONFIG_PATH.expanduser()
    if default.is_file():
        return default
    return None


def _build_config(raw: dict, source: Path) -> BplConfig:
    """Map raw YAML dict to a ``BplConfig``, ignoring unknown keys."""
    kwargs: dict[str, object] = {}

    for yaml_key, field_name in _YAML_KEY_TO_FIELD.items():
        if yaml_key in raw:
            kwargs[field_name] = raw[yaml_key]

    unknown = set(raw) - set(_YAML_KEY_TO_FIELD)
    if unknown:
        logger.warning(
            "Ignoring unknown config keys in %s: %s",
            source,
            ", ".join(sorted(unknown)),
        )

    return BplConfig(**kwargs)
