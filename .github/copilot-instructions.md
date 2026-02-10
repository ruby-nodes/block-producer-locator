# Copilot Instructions — Block Producer Locator

## Project context

This is a Python CLI tool (`bpl`) that locates block-producing nodes in
blockchain networks by IP and geographic location. Read `project.md` for goals,
`architecture.md` for system design, and `tasks.md` for the current work plan.

## Package layout

```
bpl/                    # main package
  __init__.py
  cli.py                # CLI entry point (click or argparse)
  config.py             # YAML/TOML config loading
  models.py             # NodeLocation, ProbeResult, CrawlRun dataclasses
  geoip.py              # MaxMind reader, cloud detection, region inference
  persistence.py        # SQLite helpers (upsert, migrations)
  aggregator.py         # statistics: country dist, ASN breakdown, cloud ratio
  output.py             # rich table + JSON formatters
  probes/
    __init__.py          # probe registry + abstract Probe base class
    base_l2.py           # Base probe (DNS)
    optimism.py          # Optimism probe (DNS)
    starknet.py          # Starknet probe (DNS)
    bsc.py               # BSC probe (devp2p + admin_peers + on-chain)
    tron.py              # TRON probe (java-tron HTTP API)
    ethereum.py          # Ethereum probe (devp2p, aggregate only)
```

## Coding conventions

- Python 3.11+. Use modern typing (`list[str]`, `X | None`, not
  `Optional[X]`).
- Prefer `dataclasses.dataclass` for data containers; avoid Pydantic unless
  a strong reason emerges.
- All public functions and classes need docstrings (Google style).
- Format with `ruff format`, lint with `ruff check`.
- No wildcard imports. Keep imports sorted (ruff handles this).
- Use `logging` (stdlib) — never bare `print()` outside the output renderer.

## Probe architecture

Every network probe inherits from `Probe` (defined in `bpl/probes/__init__.py`):

```python
class Probe(ABC):
    @abstractmethod
    def run(self, config: ProbeConfig) -> ProbeResult:
        """Execute the probe and return results."""
```

`ProbeResult` carries:
- `network: str`
- `mode: Literal["single", "list", "aggregate"]`
- `nodes: list[NodeLocation]`
- `meta: dict` (optional extra info)

The CLI dispatches to the right probe by network name, then pipes
`ProbeResult.nodes` through the geo-IP pipeline, persists to SQLite, and
renders output.

## Data flow

1. Probe produces raw `NodeLocation` objects (IP, port, node_id — no geo yet).
2. `geoip.enrich(nodes)` fills in city, country, ASN, org, cloud provider.
3. `persistence.save(crawl_run, nodes)` upserts into SQLite.
4. `output.render(result, format)` prints table or JSON.

## Key external dependencies

- **`devp2p` binary** (Go) — called via `subprocess`. Always respect the
  configured binary path; never hard-code `devp2p`.
- **MaxMind GeoLite2** — `GeoLite2-City.mmdb` and `GeoLite2-ASN.mmdb`. Paths
  come from config. Handle `FileNotFoundError` gracefully.
- **BSC geth node** — JSON-RPC (`admin_peers`). Endpoint from config.
- **java-tron node** — HTTP API on port 8090. Endpoint from config.

## Testing

- Use `pytest`. Fixtures go in `tests/conftest.py`.
- Mock external calls (DNS, HTTP, subprocess, MaxMind reader) — tests must
  not require live network access.
- Name test files `test_<module>.py`.

## Things to avoid

- Don't add async (asyncio/aiohttp) unless clearly justified — the tool is
  a short-lived CLI, not a long-running server.
- Don't introduce ORM layers for SQLite — raw `sqlite3` with a thin helper
  is fine.
- Don't over-abstract: each probe file should be self-contained and readable
  top-to-bottom.
