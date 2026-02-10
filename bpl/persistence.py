"""SQLite persistence: upsert logic, migrations, crawl_runs and nodes tables."""

import json
import logging
import sqlite3
import uuid
from datetime import UTC, datetime

from bpl.models import CrawlRun, NodeLocation

logger = logging.getLogger(__name__)

_SCHEMA_VERSION = 1

_SCHEMA_V1 = """\
CREATE TABLE IF NOT EXISTS crawl_runs (
    id                TEXT PRIMARY KEY,
    network           TEXT NOT NULL,
    timestamp         TEXT NOT NULL,
    node_count        INTEGER NOT NULL,
    duration_seconds  REAL NOT NULL,
    meta              TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS nodes (
    network        TEXT NOT NULL,
    ip             TEXT NOT NULL,
    port           INTEGER NOT NULL,
    node_id        TEXT,
    role           TEXT,
    label          TEXT,
    city           TEXT,
    country        TEXT,
    country_code   TEXT,
    latitude       REAL,
    longitude      REAL,
    asn            INTEGER,
    asn_org        TEXT,
    cloud_provider TEXT,
    cloud_region   TEXT,
    is_cloud       INTEGER,
    raw_data       TEXT NOT NULL DEFAULT '{}',
    first_seen     TEXT NOT NULL,
    last_seen      TEXT NOT NULL,
    crawl_run_id   TEXT,
    UNIQUE (network, ip, port)
);
"""


def init_db(db_path: str) -> sqlite3.Connection:
    """Open (or create) the SQLite database and apply pending migrations.

    Args:
        db_path: Filesystem path for the database, or ``":memory:"`` for
            an in-memory database (useful in tests).

    Returns:
        An open ``sqlite3.Connection`` with WAL journal mode and foreign
        keys enabled.
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    _migrate(conn)
    return conn


def save_crawl_run(conn: sqlite3.Connection, crawl_run: CrawlRun) -> str:
    """Persist a crawl run and assign it a UUID.

    The generated UUID is written back to ``crawl_run.id``.

    Args:
        conn: Open database connection (from ``init_db``).
        crawl_run: The crawl run to persist.

    Returns:
        The generated UUID string.
    """
    run_id = uuid.uuid4().hex
    crawl_run.id = run_id
    conn.execute(
        "INSERT INTO crawl_runs (id, network, timestamp, node_count, "
        "duration_seconds, meta) VALUES (?, ?, ?, ?, ?, ?)",
        (
            run_id,
            crawl_run.network,
            crawl_run.timestamp.isoformat(),
            crawl_run.node_count,
            crawl_run.duration_seconds,
            json.dumps(crawl_run.meta),
        ),
    )
    conn.commit()
    return run_id


def save_nodes(
    conn: sqlite3.Connection,
    nodes: list[NodeLocation],
    crawl_run_id: str,
) -> None:
    """Upsert discovered nodes into the ``nodes`` table.

    On first insert ``first_seen`` is set to the current UTC time.
    On conflict (same ``network, ip, port``), all fields are updated
    except ``first_seen``, which is preserved.

    Args:
        conn: Open database connection (from ``init_db``).
        nodes: List of node locations to upsert.
        crawl_run_id: The crawl-run UUID that discovered these nodes.
    """
    now = datetime.now(UTC).isoformat()
    rows = [
        (
            n.network,
            n.ip,
            n.port,
            n.node_id,
            n.role,
            n.label,
            n.city,
            n.country,
            n.country_code,
            n.latitude,
            n.longitude,
            n.asn,
            n.asn_org,
            n.cloud_provider,
            n.cloud_region,
            int(n.is_cloud) if n.is_cloud is not None else None,
            json.dumps(n.raw_data),
            now,  # first_seen (only used on INSERT)
            now,  # last_seen
            crawl_run_id,
        )
        for n in nodes
    ]
    conn.executemany(
        """\
        INSERT INTO nodes (
            network, ip, port, node_id, role, label,
            city, country, country_code, latitude, longitude,
            asn, asn_org, cloud_provider, cloud_region, is_cloud,
            raw_data, first_seen, last_seen, crawl_run_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (network, ip, port) DO UPDATE SET
            node_id        = excluded.node_id,
            role           = excluded.role,
            label          = excluded.label,
            city           = excluded.city,
            country        = excluded.country,
            country_code   = excluded.country_code,
            latitude       = excluded.latitude,
            longitude      = excluded.longitude,
            asn            = excluded.asn,
            asn_org        = excluded.asn_org,
            cloud_provider = excluded.cloud_provider,
            cloud_region   = excluded.cloud_region,
            is_cloud       = excluded.is_cloud,
            raw_data       = excluded.raw_data,
            last_seen      = excluded.last_seen,
            crawl_run_id   = excluded.crawl_run_id
        """,
        rows,
    )
    conn.commit()


def _migrate(conn: sqlite3.Connection) -> None:
    """Apply database migrations up to ``_SCHEMA_VERSION``.

    Uses the SQLite ``user_version`` pragma to track the current schema
    version.  Each version bump is applied in order so that databases
    created at any prior version are brought up to date.
    """
    (current,) = conn.execute("PRAGMA user_version").fetchone()

    if current >= _SCHEMA_VERSION:
        return

    if current < 1:
        logger.debug("Applying schema migration v0 → v1")
        conn.executescript(_SCHEMA_V1)

    conn.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")
    conn.commit()
    logger.debug("Database schema at version %d", _SCHEMA_VERSION)
