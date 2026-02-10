# Architectural Decision Records

<!-- Record significant technical decisions here as the project evolves.
     Use the format:

## ADR-NNN: Title

**Date:** YYYY-MM-DD
**Status:** proposed | accepted | superseded by ADR-XXX

### Context
What is the issue that we're seeing that is motivating this decision?

### Decision
What is the change that we're proposing and/or doing?

### Consequences
What becomes easier or harder because of this change?
-->

## ADR-001: Use YAML for the configuration file format

**Date:** 2026-02-10
**Status:** accepted

### Context

Task 1.3 specifies "YAML/TOML config file loading". We need to pick one
format. The config file is small (a handful of paths and URLs) and
human-edited.

TOML is available via stdlib `tomllib` (read-only, Python 3.11+). YAML
requires an external dependency (`pyyaml`) but is more commonly used for
simple key-value configuration files and is familiar to most operators.

### Decision

Use YAML (`pyyaml`) with the convention `~/.bpl/config.yaml`. The file is
optional — the tool works with pure defaults when no config file exists.

### Consequences

- One additional runtime dependency (`pyyaml>=6.0,<7`).
- Simpler syntax for the end user (no quoting rules, no table headers).
- If we later need to *write* config files programmatically, `pyyaml` supports
  dumping; `tomllib` does not (we would need `tomli-w`).


## ADR-002: No per-endpoint CLI flags; use config file only

**Date:** 2026-02-10
**Status:** accepted

### Context

The architecture diagram shows `--bsc-node URL` and `--tron-node URL` as CLI
flags. However, `BplConfig` already stores `bsc_node_url` and `tron_node_url`
and is loaded from the YAML config file (`~/.bpl/config.yaml`). Duplicating
these as CLI flags would mean two code paths for the same values, and the
number of endpoint flags will grow as probes are added.

### Decision

Keep endpoint configuration exclusively in the YAML config file. The CLI
exposes only `--network`, `--format`, and `--config`. The `--config` flag
already lets the user point to an alternate config file when needed.

### Consequences

- Simpler CLI surface — three flags instead of a growing list.
- Users who want to override a single endpoint must edit the config file (or
  pass an alternate file via `--config`). This is acceptable for a tool that
  is typically configured once per machine.
- If ad-hoc endpoint overrides become a frequent need, we can add flags later
  without breaking the existing interface.

