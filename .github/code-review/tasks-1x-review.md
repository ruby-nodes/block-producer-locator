# Code Review — Tasks 1.x (Phase 1)

**Scope**

- Review covers only tasks labeled **1.x** under **Milestone 1 — Core Infrastructure** in [TASKS.md](../../TASKS.md).
- Authoritative references: [TASKS.md](../../TASKS.md), [ARCHITECTURE.md](../../ARCHITECTURE.md), [PROJECT.md](../../PROJECT.md), [DECISIONS.md](../../DECISIONS.md).
- Review focuses on code introduced/modified to satisfy Phase 1: packaging/scaffolding, models, config, CLI, probe registry, geo-IP, persistence, output rendering, aggregator.

---

## 1) Phase 1 tasks + acceptance criteria (as written)

- **1.1** Project scaffolding: `pyproject.toml`, package layout (`bpl/`), dev dependencies (pytest, ruff)
- **1.2** Data models: `NodeLocation`, `ProbeResult`, `CrawlRun` dataclasses
- **1.3** Configuration: YAML/TOML config file loading (DB path, MaxMind DB paths, node endpoints, devp2p binary path)
- **1.4** CLI skeleton: click or argparse entry point with `--network`, `--format`, `--config` flags
- **1.5** Probe registry: abstract `Probe` base class + dynamic dispatch by network name
- **1.6** Geo-IP module: MaxMind reader (City + ASN), cloud-provider detection via static ASN map (~20 known cloud ASNs), coordinate-based region inference
- **1.7** SQLite persistence: `crawl_runs` and `nodes` tables, upsert logic, migration helper
- **1.8** Output renderer: rich table formatter + JSON formatter, output-mode dispatch (single / list / aggregate)
- **1.9** Aggregator: country distribution, ASN breakdown, cloud-vs-bare-metal ratio calculations

Notes on acceptance criteria clarity:
- Several items (1.1–1.8) specify *components* but not explicit end-to-end wiring requirements.
- [DECISIONS.md](../../DECISIONS.md) contains ADRs that narrow/clarify ambiguous items (notably 1.3 and CLI endpoint flags).

---

## 2) Evidence mapping (repo → tasks)

Status legend: **DONE / PARTIAL / MISSING / SCOPE-CREEP**

- **1.1 — DONE**
  - Packaging/config: [pyproject.toml](../../pyproject.toml)
  - Package layout: [bpl/__init__.py](../../bpl/__init__.py) and [bpl/](../../bpl/)
  - Dev deps (pytest/ruff): [pyproject.toml](../../pyproject.toml) (`[project.optional-dependencies].dev`)

- **1.2 — DONE**
  - Dataclasses: `NodeLocation`, `ProbeResult`, `CrawlRun` in [bpl/models.py](../../bpl/models.py)

- **1.3 — DONE (via ADR-001, YAML chosen)**
  - Config dataclass + loader: `BplConfig`, `load_config`, `ConfigError` in [bpl/config.py](../../bpl/config.py)
  - YAML dependency: [pyproject.toml](../../pyproject.toml) (`pyyaml`)
  - Decision narrowing “YAML/TOML”: ADR-001 in [DECISIONS.md](../../DECISIONS.md)

- **1.4 — PARTIAL**
  - CLI entry point + flags: `main` in [bpl/cli.py](../../bpl/cli.py)
  - Script entrypoint: [pyproject.toml](../../pyproject.toml) (`[project.scripts] bpl = "bpl.cli:main"`)
  - Tests covering flags/help: [tests/test_cli.py](../../tests/test_cli.py)
  - Dispatch loop exists, but architecture-described lifecycle (geo-enrich → persist → aggregate → render) is not implemented; [bpl/cli.py](../../bpl/cli.py) has an explicit TODO for geo/persist.

- **1.5 — DONE**
  - Base class + registry/dispatch: `Probe`, `get_probe`, `registered_networks` in [bpl/probes/__init__.py](../../bpl/probes/__init__.py)
  - Registry coverage tests: [tests/test_probes.py](../../tests/test_probes.py)

- **1.6 — DONE (module present + tests)**
  - GeoIP pipeline: `GeoIPReader`, `enrich`, `infer_cloud_region`, `CLOUD_ASN_MAP` in [bpl/geoip.py](../../bpl/geoip.py)
  - Unit tests: [tests/test_geoip.py](../../tests/test_geoip.py)

- **1.7 — DONE (module present + tests)**
  - SQLite helpers: `init_db`, `save_crawl_run`, `save_nodes`, `_migrate` in [bpl/persistence.py](../../bpl/persistence.py)
  - Unit tests: [tests/test_persistence.py](../../tests/test_persistence.py)

- **1.8 — DONE (module present + tests)**
  - Renderer: `render`, `render_table`, `render_json` in [bpl/output.py](../../bpl/output.py)
  - Unit tests: [tests/test_output.py](../../tests/test_output.py)

- **1.9 — MISSING**
  - Aggregator module is a stub only: [bpl/aggregator.py](../../bpl/aggregator.py)

---

## 3) Findings (only Phase 1 code)

### BLOCKER

- **Core dataflow described in architecture is not implemented in the CLI**
  - [ARCHITECTURE.md](../../ARCHITECTURE.md) and [PROJECT.md](../../PROJECT.md) describe an end-to-end pipeline: probe → geo-IP enrichment → SQLite persistence → aggregation → output.
  - The current CLI runs the probe and renders immediately; [bpl/cli.py](../../bpl/cli.py) contains an explicit `TODO(1.6–1.7): geo-enrich, persist.` and does not call `bpl.geoip.enrich` or `bpl.persistence.init_db/save_*`.
  - Impact: Phase 1 “core infrastructure” exists as separate modules, but the executable tool does not perform the project’s primary function (geo-located, persisted results).

### HIGH

- **Type-safety boundary violation in CLI dispatch**
  - `Probe.run()` is defined to accept a typed `BplConfig` per ADR-003 in [DECISIONS.md](../../DECISIONS.md) and in the signature in [bpl/probes/__init__.py](../../bpl/probes/__init__.py).
  - [bpl/cli.py](../../bpl/cli.py) defines `_run_probe(..., cfg: object)` and calls `probe.run(cfg)` with a `# type: ignore[arg-type]`.
  - Impact: undermines the “typed config” architectural decision and makes mis-wiring/incorrect config usage easier to miss.

- **Aggregator (1.9) is absent but output supports aggregate mode**
  - Aggregate-mode rendering expects specific `result.meta` keys (country/asn distributions, cloud ratio) in [bpl/output.py](../../bpl/output.py).
  - [bpl/aggregator.py](../../bpl/aggregator.py) is a stub; no Phase 1 code produces those keys.
  - Impact: “aggregate” output mode will typically degrade to “No aggregate data available” unless probes manually construct meta; this is a functional gap against 1.9.

### MED

- **Schema sets `foreign_keys=ON` but defines no FK constraints**
  - [bpl/persistence.py](../../bpl/persistence.py) enables `PRAGMA foreign_keys = ON`, but the schema does not declare `crawl_run_id` as a foreign key to `crawl_runs(id)`.
  - Impact: orphaned `nodes.crawl_run_id` values are possible; referential integrity relies on application correctness only.

- **Default filesystem paths imply “works out of the box”, but directory creation is not part of Phase 1 wiring**
  - `DEFAULT_DB_PATH` in [bpl/config.py](../../bpl/config.py) points to `~/.bpl/bpl.db`.
  - Since the CLI does not initialize the DB yet (and no code creates `~/.bpl/`), the “defaults work” story is only true for modes that don’t touch SQLite/MaxMind paths.
  - Impact: operational surprise once persistence is wired (likely “unable to open database file” if the directory is missing).

### LOW

- **Documentation drift between architecture diagram and ADRs/current CLI**
  - [ARCHITECTURE.md](../../ARCHITECTURE.md) diagram mentions endpoint CLI flags (`--bsc-node`, `--tron-node`) and shows probe signature `run(config: dict)`.
  - ADR-002 and ADR-003 in [DECISIONS.md](../../DECISIONS.md) explicitly choose config-file-only endpoints and typed `BplConfig`.
  - Impact: operator/developer confusion; multiple authoritative documents disagree on interface details.

- **Probe implementations for non-Phase-1 milestones exist as stubs and are registered**
  - All network probes currently raise `NotImplementedError` (e.g., [bpl/probes/base_l2.py](../../bpl/probes/base_l2.py), [bpl/probes/bsc.py](../../bpl/probes/bsc.py)).
  - Phase 1 tasks do not require those probes to be implemented; however, this affects CLI behavior and tests.
  - Impact: expected during early milestones, but it means the CLI’s runtime behavior is “not implemented” for all networks.
---

## 4) Review evaluation (2026-02-10)

### Finding-by-finding assessment

| # | Finding | Verdict | Justification |
|---|---------|---------|---------------|
| 1 | BLOCKER: CLI pipeline not wired (geo-enrich, persist, aggregate) | **ACCEPT** (downgrade to HIGH) | Modules exist individually but the CLI orchestrator skips them. No data is silently lost today (all probes raise `NotImplementedError`), so it is not a runtime blocker *yet*, but it must be resolved before any M2 probe lands. |
| 2 | HIGH: `_run_probe(cfg: object)` + `type: ignore` | **ACCEPT** | Directly contradicts ADR-003 (`BplConfig` typed config). Trivial fix: change the annotation, remove the suppression. |
| 3 | HIGH: Aggregator 1.9 absent | **ACCEPT** | Task 1.9 is the only unchecked M1 item. Correctly identified. Must be implemented before aggregate-mode output is meaningful. |
| 4 | MED: `foreign_keys=ON` without FK constraint | **ACCEPT** | Enabling the pragma is pointless without a declared constraint. Adding `REFERENCES crawl_runs(id)` and bumping the schema version is low-effort and prevents future orphan rows. |
| 5 | MED: Default `~/.bpl/` directory never created | **ACCEPT** | `sqlite3.connect` will raise `OperationalError` if the parent directory is missing. Must be addressed when CLI wiring lands. |
| 6 | LOW: ARCHITECTURE.md drift vs. ADR-002/003 | **ACCEPT** | Two authoritative docs disagree on CLI flags and probe signature. Documentation-only fix, no code impact. |
| 7 | LOW: Stub probes registered for non-M1 milestones | **REJECT** | Expected scaffolding used to validate the registry (task 1.5). CLI handles `NotImplementedError` gracefully. Not a defect. |

### Actionable tasks (ACCEPTED findings only)

1. **Wire CLI pipeline** — in `_run_probe`, call `geoip.enrich` → `persistence.init_db`/`save_crawl_run`/`save_nodes` → aggregator → `render`. Remove the `TODO(1.6–1.7)` comment.
2. **Fix `_run_probe` type annotation** — change `cfg: object` → `cfg: BplConfig`; remove `# type: ignore[arg-type]`.
3. **Implement task 1.9 (aggregator)** — add `country_distribution`, `asn_distribution`, `cloud_ratio` computation in `bpl/aggregator.py`; populate `ProbeResult.meta` from the CLI before rendering.
4. **Add FK constraint to schema** — declare `crawl_run_id TEXT REFERENCES crawl_runs(id)` in the nodes table; bump `_SCHEMA_VERSION` and add a v2 migration.
5. **Create `~/.bpl/` directory before DB init** — add `os.makedirs(parent, exist_ok=True)` in `init_db` or in the CLI before calling it.
6. **Update ARCHITECTURE.md** — remove `--bsc-node`/`--tron-node` flags from diagram; change `run(config: dict)` → `run(config: BplConfig)` to match ADR-002 and ADR-003.

### Readiness

**Safe to proceed to Milestone 2 without changes? NO**

**Blocking items** (must resolve before merging any M2 probe):

1. **CLI pipeline wiring** (#1) — M2 probes produce real nodes; without wiring they are never enriched or persisted.
2. **Fix `cfg: object` annotation** (#2) — trivial but blocks clean type-checking for all future probe work.
3. **Implement aggregator 1.9** (#3) — M2 task 2.5 explicitly requires verifying geo-IP enrichment, SQLite write, and output end-to-end.

Items #4–#6 are important but **non-blocking** for M2 (operational polish, not functional correctness).
