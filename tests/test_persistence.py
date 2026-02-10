"""Tests for bpl.persistence — SQLite persistence layer."""

import json

from bpl.models import CrawlRun, NodeLocation
from bpl.persistence import init_db, save_crawl_run, save_nodes


def _make_node(**overrides: object) -> NodeLocation:
    """Create a NodeLocation with sensible defaults, overridable per-field."""
    defaults: dict = {
        "ip": "1.2.3.4",
        "port": 30303,
        "network": "bsc",
    }
    defaults.update(overrides)
    return NodeLocation(**defaults)


def _make_crawl_run(**overrides: object) -> CrawlRun:
    """Create a CrawlRun with sensible defaults, overridable per-field."""
    defaults: dict = {
        "network": "bsc",
        "node_count": 5,
        "duration_seconds": 1.23,
    }
    defaults.update(overrides)
    return CrawlRun(**defaults)


# ------------------------------------------------------------------
# init_db
# ------------------------------------------------------------------


class TestInitDb:
    """Tests for init_db and schema migration."""

    def test_creates_tables(self) -> None:
        conn = init_db(":memory:")
        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        assert "crawl_runs" in tables
        assert "nodes" in tables
        conn.close()

    def test_sets_schema_version(self) -> None:
        conn = init_db(":memory:")
        (version,) = conn.execute("PRAGMA user_version").fetchone()
        assert version == 2
        conn.close()

    def test_idempotent(self) -> None:
        """Calling init_db twice on the same database does not raise."""
        conn = init_db(":memory:")
        # Simulate reopening: migrate again on the same connection.
        from bpl.persistence import _migrate

        _migrate(conn)
        (version,) = conn.execute("PRAGMA user_version").fetchone()
        assert version == 2
        conn.close()

    def test_nodes_crawl_run_id_has_fk(self) -> None:
        """nodes.crawl_run_id references crawl_runs(id)."""
        conn = init_db(":memory:")
        # Attempt to insert a node with a nonexistent crawl_run_id.
        import sqlite3

        import pytest

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO nodes (network, ip, port, raw_data, "
                "first_seen, last_seen, crawl_run_id) "
                "VALUES ('test', '1.2.3.4', 30303, '{}', "
                "'2026-01-01', '2026-01-01', 'nonexistent')"
            )
        conn.close()

    def test_creates_parent_directory(self, tmp_path) -> None:
        """init_db creates missing parent directories."""
        db_file = tmp_path / "subdir" / "deep" / "bpl.db"
        conn = init_db(str(db_file))
        assert db_file.exists()
        conn.close()


# ------------------------------------------------------------------
# save_crawl_run
# ------------------------------------------------------------------


class TestSaveCrawlRun:
    """Tests for save_crawl_run."""

    def test_inserts_row_and_returns_id(self) -> None:
        conn = init_db(":memory:")
        run = _make_crawl_run()
        run_id = save_crawl_run(conn, run)

        assert run_id
        assert run.id == run_id

        row = conn.execute(
            "SELECT * FROM crawl_runs WHERE id = ?", (run_id,)
        ).fetchone()
        assert row is not None
        assert row["network"] == "bsc"
        assert row["node_count"] == 5
        assert row["duration_seconds"] == 1.23
        conn.close()

    def test_meta_persisted_as_json(self) -> None:
        conn = init_db(":memory:")
        run = _make_crawl_run(meta={"key": "value"})
        run_id = save_crawl_run(conn, run)

        row = conn.execute(
            "SELECT meta FROM crawl_runs WHERE id = ?", (run_id,)
        ).fetchone()
        assert json.loads(row["meta"]) == {"key": "value"}
        conn.close()

    def test_multiple_runs(self) -> None:
        conn = init_db(":memory:")
        id1 = save_crawl_run(conn, _make_crawl_run(network="base"))
        id2 = save_crawl_run(conn, _make_crawl_run(network="tron"))

        assert id1 != id2
        count = conn.execute("SELECT count(*) FROM crawl_runs").fetchone()[0]
        assert count == 2
        conn.close()


# ------------------------------------------------------------------
# save_nodes
# ------------------------------------------------------------------


class TestSaveNodes:
    """Tests for save_nodes (insert and upsert)."""

    def test_insert_new_nodes(self) -> None:
        conn = init_db(":memory:")
        run_id = save_crawl_run(conn, _make_crawl_run())

        nodes = [
            _make_node(ip="10.0.0.1", port=30303),
            _make_node(ip="10.0.0.2", port=30303),
        ]
        save_nodes(conn, nodes, run_id)

        count = conn.execute("SELECT count(*) FROM nodes").fetchone()[0]
        assert count == 2
        conn.close()

    def test_first_seen_equals_last_seen_on_insert(self) -> None:
        conn = init_db(":memory:")
        run_id = save_crawl_run(conn, _make_crawl_run())
        save_nodes(conn, [_make_node()], run_id)

        row = conn.execute("SELECT first_seen, last_seen FROM nodes").fetchone()
        assert row["first_seen"] == row["last_seen"]
        conn.close()

    def test_upsert_preserves_first_seen(self) -> None:
        conn = init_db(":memory:")
        run_id = save_crawl_run(conn, _make_crawl_run())

        node = _make_node(ip="10.0.0.1", city="Berlin")
        save_nodes(conn, [node], run_id)
        row1 = conn.execute("SELECT first_seen, last_seen FROM nodes").fetchone()
        original_first_seen = row1["first_seen"]

        # Upsert with updated geo data.
        node_updated = _make_node(ip="10.0.0.1", city="Paris")
        save_nodes(conn, [node_updated], run_id)

        row2 = conn.execute("SELECT first_seen, last_seen, city FROM nodes").fetchone()
        assert row2["first_seen"] == original_first_seen
        assert row2["city"] == "Paris"
        conn.close()

    def test_upsert_updates_last_seen(self) -> None:
        conn = init_db(":memory:")
        run_id = save_crawl_run(conn, _make_crawl_run())

        save_nodes(conn, [_make_node()], run_id)
        row1 = conn.execute("SELECT last_seen FROM nodes").fetchone()

        save_nodes(conn, [_make_node()], run_id)
        row2 = conn.execute("SELECT last_seen FROM nodes").fetchone()

        # last_seen should be >= the previous value (may be equal if very fast).
        assert row2["last_seen"] >= row1["last_seen"]
        conn.close()

    def test_all_fields_round_trip(self) -> None:
        conn = init_db(":memory:")
        run_id = save_crawl_run(conn, _make_crawl_run())

        node = NodeLocation(
            ip="192.168.1.1",
            port=8545,
            network="bsc",
            node_id="enode://abc123",
            role="validator",
            label="Validator-1",
            city="Frankfurt",
            country="Germany",
            country_code="DE",
            latitude=50.1109,
            longitude=8.6821,
            asn=16509,
            asn_org="Amazon.com, Inc.",
            cloud_provider="AWS",
            cloud_region="eu-central-1",
            is_cloud=True,
            raw_data={"client": "Geth/v1.0"},
        )
        save_nodes(conn, [node], run_id)

        row = conn.execute("SELECT * FROM nodes WHERE ip = '192.168.1.1'").fetchone()
        assert row["network"] == "bsc"
        assert row["port"] == 8545
        assert row["node_id"] == "enode://abc123"
        assert row["role"] == "validator"
        assert row["label"] == "Validator-1"
        assert row["city"] == "Frankfurt"
        assert row["country"] == "Germany"
        assert row["country_code"] == "DE"
        assert row["latitude"] == 50.1109
        assert row["longitude"] == 8.6821
        assert row["asn"] == 16509
        assert row["asn_org"] == "Amazon.com, Inc."
        assert row["cloud_provider"] == "AWS"
        assert row["cloud_region"] == "eu-central-1"
        assert row["is_cloud"] == 1  # SQLite stores booleans as integers
        assert json.loads(row["raw_data"]) == {"client": "Geth/v1.0"}
        assert row["crawl_run_id"] == run_id
        conn.close()

    def test_different_networks_same_ip(self) -> None:
        """Nodes on different networks with the same IP are distinct rows."""
        conn = init_db(":memory:")
        run_id = save_crawl_run(conn, _make_crawl_run())

        save_nodes(
            conn,
            [
                _make_node(ip="10.0.0.1", network="bsc"),
                _make_node(ip="10.0.0.1", network="ethereum"),
            ],
            run_id,
        )

        count = conn.execute("SELECT count(*) FROM nodes").fetchone()[0]
        assert count == 2
        conn.close()

    def test_empty_node_list(self) -> None:
        """Saving an empty list does not raise."""
        conn = init_db(":memory:")
        run_id = save_crawl_run(conn, _make_crawl_run())
        save_nodes(conn, [], run_id)

        count = conn.execute("SELECT count(*) FROM nodes").fetchone()[0]
        assert count == 0
        conn.close()
