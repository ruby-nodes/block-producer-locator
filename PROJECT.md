# Block Producer Locator

## Overview

A Python CLI tool that identifies block-producing nodes in blockchain networks
by their IP addresses and physical (geographic) locations. It targets both
Layer-2 centralized sequencers and Layer-1 Proof-of-Authority / Proof-of-Stake
validator sets.

## Goals

1. Resolve the IP addresses of block-producing infrastructure for each
   supported network.
2. Geolocate those IPs — city, country, ASN, and cloud provider / data-center
   when applicable.
3. Present results in three output modes tailored to the network's scale:
   **single** (one sequencer), **list** (tens of validators), and
   **aggregate** (thousands of nodes).
4. Persist every crawl to SQLite so results can be compared over time.

## Supported Networks

| Network   | Category          | Discovery method                                 | Output mode |
|-----------|-------------------|--------------------------------------------------|-------------|
| Base      | L2 sequencer      | DNS resolution of sequencer endpoint              | single      |
| Optimism  | L2 sequencer      | DNS resolution of sequencer endpoint              | single      |
| Starknet  | L2 sequencer      | DNS resolution of gateway endpoint                | single      |
| BSC       | PoSA validators   | `devp2p discv4 crawl` + `admin_peers` + on-chain  | list        |
| TRON      | DPoS super reps   | java-tron HTTP API (`listnodes` + `listwitnesses`) | list        |
| Ethereum  | PoS validators    | `devp2p discv4 crawl` (aggregate only)            | aggregate   |

## Discovery Approaches

### L2 Sequencers (Base, Optimism, Starknet)

L2 sequencers sit behind CDN / load-balancer infrastructure. The best we can
do without running a modified node is DNS resolution, yielding the CDN edge or
cloud-region IP. This gives **cloud region / data-center accuracy**, which the
user has accepted as sufficient.

Endpoints:
- Base: `mainnet-sequencer.base.org`
- Optimism: `mainnet-sequencer.optimism.io`
- Starknet: `alpha-mainnet.starknet.io`

### BSC (BNB Smart Chain)

BSC uses the same devp2p stack as Ethereum. Discovery combines:

1. **DHT crawl** — `devp2p discv4 crawl` with BSC bootnodes to find all
   reachable peers in the DHT.
2. **admin_peers** — JSON-RPC call against the user's own BSC geth node to get
   currently connected peers with their IPs.
3. **On-chain validator set** — Query the StakeHub contract
   (`0x0000000000000000000000000000000000002002`) or the `getValidators` RPC
   for the active validator set.
4. **Correlation** — Match enode IDs from DHT/peers against on-chain validator
   keys to separate validators from ordinary full nodes.

### TRON

TRON's java-tron exposes HTTP APIs on port 8090:

- `wallet/listnodes` — returns all connected peers (IP + port).
- `wallet/listwitnesses` — returns the 27 active Super Representatives with
  addresses.
- Correlation maps SR addresses to node IPs through the peer list.

### Ethereum

Ethereum has ~10 000 nodes in the DHT. We crawl with `devp2p discv4 crawl`
and produce **aggregate statistics only** (country distribution, ASN
breakdown, cloud vs. bare-metal ratio). Individual validator identification is
out of scope (see Heimbach et al., USENIX Security 2025, for the complexity
involved).

## Tech Stack

- **Python 3.11+** — main application
- **geoip2** — MaxMind GeoLite2 database reader (City + ASN)
- **rich** — terminal tables and progress bars
- **requests** — HTTP calls to TRON and L2 endpoints
- **web3** — BSC JSON-RPC interaction (admin_peers, on-chain queries)
- **Go `devp2p`** — external binary for DHT crawling (Ethereum & BSC)
- **SQLite** — persistence via the standard library `sqlite3` module

## Prerequisites

| Requirement            | Purpose                                        |
|------------------------|-------------------------------------------------|
| Python ≥ 3.11         | Runtime                                         |
| Go toolchain           | Build `devp2p` binary                           |
| `devp2p` binary        | `go install github.com/ethereum/go-ethereum/cmd/devp2p@latest` |
| MaxMind GeoLite2 DBs   | `GeoLite2-City.mmdb` + `GeoLite2-ASN.mmdb` (free account) |
| BSC geth node          | admin API enabled, JSON-RPC accessible          |
| java-tron node         | HTTP API on port 8090                           |

## Output Formats

The CLI supports `--format table` (default, human-readable via `rich`) and
`--format json` (machine-readable).

## Persistence

Every crawl run is stored in SQLite:

- **`crawl_runs`** — timestamp, network, node count, duration.
- **`nodes`** — IP, port, network, node_id, city, country, ASN, org, cloud
  provider, latitude, longitude. Upserted on `(network, ip, port)`.
