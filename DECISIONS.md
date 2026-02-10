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

