# Architecture

## Overview

Block Producer Locator is a Python CLI tool that discovers block-producing nodes across multiple blockchain networks, geolocates them, and persists results in SQLite. It uses a probe-based plugin architecture where each network has its own discovery module, but all share a common geo-IP pipeline, persistence layer, and output renderer.

## System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI (cli.py)                            │
│  --network {base,optimism,starknet,bsc,tron,ethereum,all}       │
│  --format {table,json}  --config PATH                           │
└──────────┬──────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Probe Dispatcher                            │
│         Selects and runs probe(s) based on --network            │
└──┬──────────┬──────────┬──────────┬─────────────────────────────┘
   │          │          │          │
   ▼          ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌──────────┐
│  L2    │ │  BSC   │ │  TRON  │ │ Ethereum │
│Sequen- │ │ Probe  │ │ Probe  │ │  Probe   │
│cer     │ │        │ │        │ │          │
│ Probe  │ │        │ │        │ │          │
└───┬────┘ └───┬────┘ └───┬────┘ └────┬─────┘
    │          │          │           │
    │ DNS      │ devp2p   │ HTTP API  │ devp2p
    │ resolve  │ crawl +  │ wallet/   │ crawl
    │          │ admin_   │ listnodes │
    │          │ peers +  │ wallet/   │
    │          │ web3     │ list-     │
    │          │          │ witnesses │
    │          │          │           │
    ▼          ▼          ▼           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    List[NodeLocation]                            │
│          (ip, port, node_id, role, label, ...)                  │
└──────────┬──────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Geo-IP Pipeline (geo.py)                        │
│  MaxMind GeoLite2-City  →  city, country, lat, lon              │
│  MaxMind GeoLite2-ASN   →  asn, asn_org                        │
│  Cloud Provider Map     →  cloud_provider, is_cloud             │
│  Region Inference       →  cloud_region (e.g. "eu-central-1")   │
└──────────┬──────────────────────────────────────────────────────┘
           │
       ┌───┴───┐
       ▼       ▼
┌──────────┐ ┌──────────────────────────────────────────────────┐
│  SQLite  │ │              Aggregator                          │
│   DB     │ │  country_distribution, asn_distribution,         │
│ (db.py)  │ │  cloud_vs_bare_metal, cloud_provider_by_region,  │
│          │ │  coordinates (heatmap)                            │
└──────────┘ └──────────┬───────────────────────────────────────┘
                        │
                        ▼
              ┌────────────────────┐
              │  Output Renderer   │
              │   (output.py)      │
              │                    │
              │  single → 1 row    │
              │  list   → table +  │
              │           summary  │
              │  aggregate → stats │
              │           only     │
              │                    │
              │  table (rich) or   │
              │  JSON              │
              └────────────────────┘
```

## Component Responsibilities

### Probes (`probes/`)

Each probe implements the `Probe` abstract base class:

```python
class Probe(ABC):
    @abstractmethod
    def run(self, config: BplConfig) -> ProbeResult:
        ...
```

| Probe | Networks | Discovery Method | Output Mode |
|-------|----------|-----------------|-------------|
| `L2SequencerProbe` | Base, Optimism, Starknet | `socket.getaddrinfo()` + optional `dig`/`traceroute` | single |
| `BSCProbe` | BSC | `devp2p discv4 crawl` (subprocess) + `admin_peers` RPC + `StakeHub` contract query | list |
| `TRONProbe` | TRON | `wallet/listnodes` + `wallet/listwitnesses` HTTP API on java-tron | list |
| `EthereumProbe` | Ethereum | `devp2p discv4 crawl` (subprocess) | aggregate |

### Geo-IP Pipeline (`geo.py`)

Two MaxMind database lookups per IP:

1. **GeoLite2-City.mmdb** → city, country, latitude, longitude
2. **GeoLite2-ASN.mmdb** → ASN number, organization name

Plus two derived fields:

3. **Cloud provider** — static ASN→provider mapping (~20 known cloud ASNs)
4. **Cloud region** — nearest-datacenter matching from provider's known DC coordinates

### Persistence (`db.py`)

SQLite database with two tables:

- **`nodes`** — one row per `(network, ip, port)`. Upserts on each crawl: updates `last_seen` and geo fields, preserves `first_seen`. Stores `raw_data` JSON blob for network-specific metadata (enode, client version, vote count, etc.)
- **`crawl_runs`** — audit log of each probe execution with timestamp, node count, and duration

### Aggregator (`aggregator.py`)

Takes `List[NodeLocation]`, returns `AggregatedResult` with:

- Country distribution (sorted desc)
- ASN / org distribution (sorted desc)
- Cloud vs bare-metal percentage
- Cloud provider by region (e.g. `{"AWS/us-east-1": 1200}`)
- Raw coordinate list for external heatmap rendering

### Output Renderer (`output.py`)

Adapts display to the probe's `output_mode`:

| Mode | When | What's Shown |
|------|------|-------------|
| `single` | L2 sequencers | 1 row per sequencer endpoint: IP, geo, cloud info |
| `list` | BSC, TRON | Full peer table (role, label, IP, geo) + aggregation summary |
| `aggregate` | Ethereum | Stats tables only: country top-10, ASN top-10, cloud breakdown |

## External Dependencies

| Dependency | Used By | Purpose |
|------------|---------|---------|
| `devp2p` Go binary | BSC probe, Ethereum probe | DHT crawl via `devp2p discv4 crawl` |
| BSC geth node | BSC probe | `admin_peers` RPC + `eth_call` for validator set |
| java-tron node | TRON probe | `wallet/listnodes` + `wallet/listwitnesses` HTTP API |
| MaxMind GeoLite2 DBs | geo.py | IP → location + ASN (free, requires maxmind.com registration) |

## Data Flow

```
1. CLI parses args, loads config
2. Probe.run(config) executes network-specific discovery
3. Probe returns raw IPs + metadata as List[NodeLocation]
4. geo.py enriches each NodeLocation with city/country/lat/lon/ASN/cloud
5. db.py upserts enriched nodes into SQLite
6. aggregator.py computes stats from the node list
7. output.py renders based on output_mode + format preference
```

## Adding a New Network

1. Create `probes/new_network.py` implementing `Probe.run() -> ProbeResult`
2. Register it in the probe dispatcher (dict mapping in `main.py`)
3. That's it — geo-IP, persistence, aggregation, and output work automatically

For OP Stack L2s (Zora, Mode, etc.): add one entry to the endpoint map in `l2_sequencer.py`. ~1 line of code.
