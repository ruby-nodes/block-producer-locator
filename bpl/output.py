"""Output renderer: rich table formatter, JSON formatter, output-mode dispatch."""

import dataclasses
import json
import logging
import sys
from io import StringIO

from rich.console import Console
from rich.table import Table

from bpl.models import ProbeResult

logger = logging.getLogger(__name__)

# Columns displayed for single / list modes.
_NODE_COLUMNS_SINGLE = [
    ("IP", "ip"),
    ("Port", "port"),
    ("City", "city"),
    ("Country", "country"),
    ("ASN", "asn"),
    ("Org", "asn_org"),
    ("Cloud", "cloud_provider"),
    ("Region", "cloud_region"),
]

_NODE_COLUMNS_LIST = [
    ("IP", "ip"),
    ("Port", "port"),
    ("Role", "role"),
    ("Label", "label"),
    ("City", "city"),
    ("Country", "country"),
    ("Org", "asn_org"),
    ("Cloud", "cloud_provider"),
]

# How many entries to show in aggregate top-N tables.
_TOP_N = 10


def render(
    result: ProbeResult,
    fmt: str,
    *,
    file: object | None = None,
    width: int | None = None,
) -> None:
    """Dispatch output to the appropriate formatter.

    Args:
        result: Probe result to render.
        fmt: Output format — ``"table"`` or ``"json"``.
        file: Writable file object for output (default: ``sys.stdout``).
        width: Explicit console width (default: auto-detect).

    Raises:
        ValueError: If *fmt* is not ``"table"`` or ``"json"``.
    """
    if fmt == "table":
        render_table(result, file=file, width=width)
    elif fmt == "json":
        render_json(result, file=file)
    else:
        raise ValueError(f"Unknown output format: {fmt!r}")


# ---------------------------------------------------------------------------
# Table (rich) formatter
# ---------------------------------------------------------------------------


def render_table(
    result: ProbeResult,
    *,
    file: object | None = None,
    width: int | None = None,
) -> None:
    """Render *result* as a ``rich`` table to *file*.

    Behaviour adapts to ``result.mode``:

    * **single** — one row per node with geo / cloud fields.
    * **list** — full node table plus a summary line.
    * **aggregate** — stats-only tables (top countries, ASNs, cloud ratio).

    Args:
        result: Probe result to render.
        file: Writable file object (default: ``sys.stdout``).
        width: Explicit console width (default: auto-detect).
    """
    out = file or sys.stdout
    console = Console(file=out, highlight=False, width=width)

    if result.mode == "single":
        _render_table_single(console, result)
    elif result.mode == "list":
        _render_table_list(console, result)
    elif result.mode == "aggregate":
        _render_table_aggregate(console, result)
    else:
        logger.warning("Unknown output mode %r, falling back to list", result.mode)
        _render_table_list(console, result)


def _render_table_single(console: Console, result: ProbeResult) -> None:
    """Render a minimal table for single-endpoint probes (L2 sequencers)."""
    table = Table(title=f"{result.network} — sequencer")
    for header, _ in _NODE_COLUMNS_SINGLE:
        table.add_column(header)

    for node in result.nodes:
        table.add_row(*[_fmt(getattr(node, attr)) for _, attr in _NODE_COLUMNS_SINGLE])

    console.print(table)


def _render_table_list(console: Console, result: ProbeResult) -> None:
    """Render a full node table plus a summary line."""
    table = Table(title=f"{result.network} — {len(result.nodes)} nodes")
    for header, _ in _NODE_COLUMNS_LIST:
        table.add_column(header)

    for node in result.nodes:
        table.add_row(*[_fmt(getattr(node, attr)) for _, attr in _NODE_COLUMNS_LIST])

    console.print(table)
    _print_list_summary(console, result)


def _print_list_summary(console: Console, result: ProbeResult) -> None:
    """Print a one-line summary beneath the list table."""
    nodes = result.nodes
    total = len(nodes)
    cloud_count = sum(1 for n in nodes if n.is_cloud)
    cloud_pct = (cloud_count / total * 100) if total else 0.0

    # Top country.
    countries: dict[str, int] = {}
    for n in nodes:
        if n.country:
            countries[n.country] = countries.get(n.country, 0) + 1
    top_country = max(countries, key=countries.get) if countries else "—"  # type: ignore[arg-type]

    console.print(
        f"  {total} nodes, {cloud_count} cloud ({cloud_pct:.0f}%), "
        f"top country: {top_country}"
    )


def _render_table_aggregate(console: Console, result: ProbeResult) -> None:
    """Render aggregate stats tables from ``result.meta``.

    Expected keys in ``result.meta`` (populated by the aggregator):

    * ``country_distribution`` — ``list[tuple[str, int]]`` sorted desc.
    * ``asn_distribution`` — ``list[tuple[str, int]]`` sorted desc.
    * ``cloud_ratio`` — ``dict`` with ``cloud``, ``bare_metal``, ``total``.
    """
    meta = result.meta

    console.print(f"\n[bold]{result.network} — aggregate statistics[/bold]\n")

    # -- Country distribution --
    country_dist = meta.get("country_distribution", [])
    if country_dist:
        t = Table(title="Top countries")
        t.add_column("Country")
        t.add_column("Nodes", justify="right")
        for country, count in country_dist[:_TOP_N]:
            t.add_row(country, str(count))
        console.print(t)

    # -- ASN distribution --
    asn_dist = meta.get("asn_distribution", [])
    if asn_dist:
        t = Table(title="Top ASNs")
        t.add_column("ASN / Org")
        t.add_column("Nodes", justify="right")
        for asn_label, count in asn_dist[:_TOP_N]:
            t.add_row(asn_label, str(count))
        console.print(t)

    # -- Cloud vs bare-metal --
    cloud_ratio = meta.get("cloud_ratio", {})
    if cloud_ratio:
        t = Table(title="Cloud vs bare-metal")
        t.add_column("Category")
        t.add_column("Nodes", justify="right")
        t.add_row("Cloud", str(cloud_ratio.get("cloud", 0)))
        t.add_row("Bare-metal", str(cloud_ratio.get("bare_metal", 0)))
        t.add_row("Total", str(cloud_ratio.get("total", 0)))
        console.print(t)

    if not (country_dist or asn_dist or cloud_ratio):
        console.print("  No aggregate data available.")


# ---------------------------------------------------------------------------
# JSON formatter
# ---------------------------------------------------------------------------


def render_json(result: ProbeResult, *, file: object | None = None) -> None:
    """Render *result* as JSON to *file*.

    For **single** and **list** modes the output is an object with ``network``,
    ``mode``, ``nodes`` (list of node dicts), and ``meta``.

    For **aggregate** mode the output is the same structure; consumers should
    look at ``meta`` for the stats.

    Args:
        result: Probe result to render.
        file: Writable file object (default: ``sys.stdout``).
    """
    out = file or sys.stdout
    payload = _probe_result_to_dict(result)
    json.dump(payload, out, indent=2, default=str)
    out.write("\n")  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _probe_result_to_dict(result: ProbeResult) -> dict:
    """Convert a ``ProbeResult`` (and its nodes) to a plain dict."""
    return {
        "network": result.network,
        "mode": result.mode,
        "nodes": [dataclasses.asdict(n) for n in result.nodes],
        "meta": result.meta,
    }


def _fmt(value: object) -> str:
    """Format a field value for table display.

    ``None`` becomes ``"—"``, everything else is stringified.
    """
    if value is None:
        return "—"
    return str(value)


def render_to_string(result: ProbeResult, fmt: str, *, width: int = 200) -> str:
    """Render to a string instead of stdout — useful for testing.

    Args:
        result: Probe result to render.
        fmt: Output format — ``"table"`` or ``"json"``.
        width: Console width for table rendering (default: 200).

    Returns:
        The rendered output as a string.
    """
    buf = StringIO()
    render(result, fmt, file=buf, width=width)
    return buf.getvalue()
