"""Named data migrations run exactly once; the smalltech.in one re-parents only the rows it should."""

import logging
import uuid

import pytest

from core import db_pool, schema

NAME = schema.SMALLTECH_SUBDOMAINS_MIGRATION


@pytest.fixture
def cur():
    """A cursor in a transaction that is rolled back, so the shared test database is never changed."""
    with db_pool.get_connection() as conn:
        with conn.cursor() as c:
            c.execute("SELECT 1 FROM tenants WHERE name = %s", (schema.SMALLTECH_TENANT,))
            if c.fetchone() is None:
                c.execute("INSERT INTO tenants (name, enabled) VALUES (%s, TRUE)", (schema.SMALLTECH_TENANT,))
            c.execute("DELETE FROM data_migrations WHERE name = %s", (NAME,))
            yield c
        conn.rollback()


def run(c):
    schema.ensure_data_migrations_applied(c.connection)


def parent_of(c, address):
    c.execute("SELECT parent FROM domains WHERE address = %s", (address,))
    return c.fetchone()[0]


def add(c, key, address, parent, tenant_name=schema.SMALLTECH_TENANT):
    c.execute(
        "INSERT INTO domains (key, address, parent, tenant_id) "
        "VALUES (%s, %s, %s, (SELECT id FROM tenants WHERE name = %s ORDER BY id LIMIT 1)) RETURNING id",
        (key, address, parent, tenant_name),
    )
    return c.fetchone()[0]


@pytest.fixture
def world(cur):
    """COMMON, a SMALLTECH main row and a mix of rows the migration must and must not touch."""
    cur.execute("SELECT id FROM domains WHERE key = 'COMMON' ORDER BY id LIMIT 1")
    common = cur.fetchone()[0]
    # A SMALLTECH row from a real database would be in the way of the fixed address.
    cur.execute("UPDATE domains SET address = 'old-' || address WHERE key = 'SMALLTECH' AND address = 'smalltech.in'")
    tag = uuid.uuid4().hex[:6]
    cur.execute("INSERT INTO tenants (name) VALUES (%s) RETURNING id", (f"other-{tag}",))
    other = f"other-{tag}"
    main = add(cur, "SMALLTECH", "smalltech.in", common)
    add(cur, "SMALLTECH", "www.smalltech.in", common)
    add(cur, f"SUB_{tag}", f"sub-{tag}.smalltech.in", common)
    add(cur, f"DEEP_{tag}", f"deep-{tag}.smalltech.in", main)  # already under someone else: left alone
    add(cur, f"OTH_{tag}", f"oth-{tag}.smalltech.in", common, tenant_name=other)
    add(cur, f"EXT_{tag}", f"ext-{tag}.example.org", common)
    return {"common": common, "main": main, "tag": tag}


def test_it_reparents_only_the_smalltech_subdomains_under_common(cur, world, caplog):
    tag = world["tag"]
    with caplog.at_level(logging.INFO, logger="core.schema"):
        run(cur)
    assert parent_of(cur, f"sub-{tag}.smalltech.in") == world["main"]
    # www shares the SMALLTECH key and stays on COMMON; the main row is not its own parent.
    assert parent_of(cur, "www.smalltech.in") == world["common"]
    assert parent_of(cur, "smalltech.in") == world["common"]
    # Other tenants, other domains and rows with another parent are untouched.
    assert parent_of(cur, f"oth-{tag}.smalltech.in") == world["common"]
    assert parent_of(cur, f"ext-{tag}.example.org") == world["common"]
    assert parent_of(cur, f"deep-{tag}.smalltech.in") == world["main"]
    logged = [r.getMessage() for r in caplog.records if NAME in r.getMessage()]
    assert any(f"key=SUB_{tag} address=sub-{tag}.smalltech.in" in m for m in logged)
    assert not any(f"OTH_{tag}" in m or "www.smalltech.in" in m for m in logged)


def test_it_runs_once_so_later_manual_changes_survive_a_restart(cur, world):
    tag = world["tag"]
    run(cur)
    cur.execute("SELECT count(*) FROM data_migrations WHERE name = %s", (NAME,))
    assert cur.fetchone()[0] == 1
    # An owner moves the property back to COMMON, and a new matching row appears: neither is touched again.
    cur.execute("UPDATE domains SET parent = %s WHERE address = %s", (world["common"], f"sub-{tag}.smalltech.in"))
    add(cur, f"NEW_{tag}", f"new-{tag}.smalltech.in", world["common"])
    run(cur)
    run(cur)
    assert parent_of(cur, f"sub-{tag}.smalltech.in") == world["common"]
    assert parent_of(cur, f"new-{tag}.smalltech.in") == world["common"]
    cur.execute("SELECT count(*) FROM data_migrations WHERE name = %s", (NAME,))
    assert cur.fetchone()[0] == 1


def test_without_a_smalltech_row_it_is_recorded_and_changes_nothing(cur):
    cur.execute("UPDATE domains SET address = 'old-' || address WHERE key = 'SMALLTECH' AND address = 'smalltech.in'")
    cur.execute("SELECT id FROM domains WHERE key = 'COMMON' ORDER BY id LIMIT 1")
    common = cur.fetchone()[0]
    tag = uuid.uuid4().hex[:6]
    add(cur, f"SUB_{tag}", f"sub-{tag}.smalltech.in", common)
    run(cur)
    assert parent_of(cur, f"sub-{tag}.smalltech.in") == common
    cur.execute("SELECT count(*) FROM data_migrations WHERE name = %s", (NAME,))
    assert cur.fetchone()[0] == 1
    # The row is created later: the migration is already recorded and never re-runs.
    add(cur, "SMALLTECH", "smalltech.in", common)
    run(cur)
    assert parent_of(cur, f"sub-{tag}.smalltech.in") == common


def test_every_migration_name_is_unique():
    names = [name for name, _ in schema.DATA_MIGRATIONS]
    assert len(names) == len(set(names)) and NAME in names
