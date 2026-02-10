"""CLI entry point for the bpl tool."""

import logging
import sys
import time

import click

from bpl.aggregator import aggregate_to_meta
from bpl.config import BplConfig, ConfigError, load_config
from bpl.geoip import enrich
from bpl.models import CrawlRun
from bpl.output import render
from bpl.persistence import init_db, save_crawl_run, save_nodes
from bpl.probes import get_probe, registered_networks

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

    networks = registered_networks() if network == "all" else [network]

    for net in networks:
        _run_probe(net, output_format, cfg)


def _run_probe(network: str, output_format: str, cfg: BplConfig) -> None:
    """Dispatch to a single probe and run the full pipeline.

    Pipeline: probe → geo-enrich → persist → aggregate → render.

    Args:
        network: Network name to probe.
        output_format: Output format (``"table"`` or ``"json"``).
        cfg: Loaded ``BplConfig`` instance.
    """
    try:
        probe = get_probe(network)
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        return

    try:
        t0 = time.monotonic()
        result = probe.run(cfg)
        duration = time.monotonic() - t0
    except NotImplementedError:
        click.echo(
            f"bpl: network={network}, format={output_format} "
            f"(probe not yet implemented)"
        )
        return

    # Geo-IP enrichment.
    enrich(result.nodes, cfg)

    # Persistence.
    conn = init_db(cfg.db_path)
    try:
        crawl_run = CrawlRun(
            network=network,
            node_count=len(result.nodes),
            duration_seconds=duration,
        )
        run_id = save_crawl_run(conn, crawl_run)
        save_nodes(conn, result.nodes, run_id)
    finally:
        conn.close()

    # Aggregation (populate meta for aggregate / list modes).
    if result.mode in ("aggregate", "list"):
        result.meta.update(aggregate_to_meta(result.nodes))

    render(result, output_format)
