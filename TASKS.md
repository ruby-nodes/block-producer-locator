# Tasks

## Milestone 1 — Core Infrastructure

Everything shared across probes: models, configuration, geo-IP pipeline,
persistence, output rendering, and the CLI entry point.

- [x] **1.1** Project scaffolding: `pyproject.toml`, package layout (`bpl/`),
      dev dependencies (pytest, ruff)
- [x] **1.2** Data models: `NodeLocation`, `ProbeResult`, `CrawlRun`
      dataclasses
- [x] **1.3** Configuration: YAML/TOML config file loading (DB path, MaxMind
      DB paths, node endpoints, devp2p binary path)
- [x] **1.4** CLI skeleton: `click` or `argparse` entry point with
      `--network`, `--format`, `--config` flags
- [x] **1.5** Probe registry: abstract `Probe` base class + dynamic dispatch
      by network name
- [x] **1.6** Geo-IP module: MaxMind reader (City + ASN), cloud-provider
      detection via static ASN map (~20 known cloud ASNs), coordinate-based
      region inference
- [x] **1.7** SQLite persistence: `crawl_runs` and `nodes` tables, upsert
      logic, migration helper
- [x] **1.8** Output renderer: `rich` table formatter + JSON formatter,
      output-mode dispatch (single / list / aggregate)
- [ ] **1.9** Aggregator: country distribution, ASN breakdown,
      cloud-vs-bare-metal ratio calculations

## Milestone 2 — L2 Sequencer Probes

Simple DNS-based probes, good first end-to-end validation of the full
pipeline.

- [x] **2.1** DNS resolution helper: `socket.getaddrinfo` wrapper returning
      all A/AAAA records
- [ ] **2.2** Base probe: resolve `mainnet-sequencer.base.org`, produce
      `ProbeResult(mode="single")`
- [ ] **2.3** Optimism probe: resolve `mainnet-sequencer.optimism.io`
- [ ] **2.4** Starknet probe: resolve `alpha-mainnet.starknet.io`
- [ ] **2.5** End-to-end test: run one L2 probe, verify geo-IP enrichment,
      SQLite write, table + JSON output

## Milestone 3 — BSC Probe

Combines DHT crawling, admin API, and on-chain data to identify the ~21
active validators.

- [ ] **3.1** `devp2p` wrapper: subprocess launcher for
      `devp2p discv4 crawl`, JSON output parser, configurable bootnodes +
      timeout
- [ ] **3.2** `admin_peers` fetcher: JSON-RPC call via `web3.py` provider,
      parse enode ID + remote IP
- [ ] **3.3** On-chain validator set: query `getValidators` or StakeHub
      contract for current active validators
- [ ] **3.4** Validator correlation: match enode public keys from DHT / peers
      to on-chain validator keys
- [ ] **3.5** BSC probe integration: orchestrate the above, produce
      `ProbeResult(mode="list")`
- [ ] **3.6** Test with live BSC geth node

## Milestone 4 — TRON Probe

HTTP API-based probe against a running java-tron full node.

- [ ] **4.1** TRON API client: `requests`-based wrapper for java-tron HTTP
      API (configurable host + port)
- [ ] **4.2** `wallet/listnodes` fetcher: parse peer list into `(ip, port)`
      tuples
- [ ] **4.3** `wallet/listwitnesses` fetcher: parse Super Representative list
      (address, vote count, url)
- [ ] **4.4** SR-to-node correlation: match SR addresses to peer IPs
- [ ] **4.5** TRON probe integration: orchestrate the above, produce
      `ProbeResult(mode="list")`
- [ ] **4.6** Test with live java-tron node

## Milestone 5 — Ethereum Probe

DHT crawl producing aggregate-only statistics (no individual validator
identification).

- [ ] **5.1** Reuse `devp2p` wrapper from M3 with Ethereum mainnet bootnodes
- [ ] **5.2** Ethereum probe: run crawl, geo-locate all discovered IPs,
      produce `ProbeResult(mode="aggregate")`
- [ ] **5.3** Aggregation output: country table, top-N ASNs,
      cloud-vs-bare-metal pie-chart (text representation)
- [ ] **5.4** Handle large crawl results efficiently (streaming geo-IP
      lookups, batched SQLite inserts)

## Milestone 6 — Polish & Documentation

Harden the tool, add tests, write user-facing documentation.

- [ ] **6.1** Error handling: network timeouts, missing MaxMind DBs,
      unreachable nodes, missing devp2p binary
- [ ] **6.2** Logging: structured logging with `--verbose` / `--quiet` flags
- [ ] **6.3** Unit tests: geo-IP module, aggregator, output renderer, config
      loading
- [ ] **6.4** Integration tests: mock-based probe tests
- [ ] **6.5** README: installation, configuration, usage examples, sample
      output
- [ ] **6.6** CI: GitHub Actions workflow for lint + test
