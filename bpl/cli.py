"""CLI entry point for the bpl tool."""

import logging
import sys

import click

from bpl.config import ConfigError, load_config

logger = logging.getLogger(__name__)

NETWORKS = ("base", "optimism", "starknet", "bsc", "tron", "ethereum", "all")
FORMATS = ("table", "json")


@click.command()
@click.option(
    "--network",
    "-n",
    required=True,
    type=click.Choice(NETWORKS, case_sensitive=False),
    help="Blockchain network to probe.",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    default="table",
    type=click.Choice(FORMATS, case_sensitive=False),
    show_default=True,
    help="Output format.",
)
@click.option(
    "--config",
    "-c",
    "config_path",
    default=None,
    type=click.Path(exists=False),
    help="Path to YAML config file (default: ~/.bpl/config.yaml).",
)
def main(network: str, output_format: str, config_path: str | None) -> None:
    """Locate block-producing nodes in blockchain networks."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    try:
        cfg = load_config(config_path)
    except (ConfigError, FileNotFoundError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    logger.debug("Config loaded: %s", cfg)

    # TODO(1.5): dispatch to probe registry based on *network*.
    click.echo(
        f"bpl: network={network}, format={output_format} "
        f"(probe dispatch not yet implemented — see task 1.5)"
    )
