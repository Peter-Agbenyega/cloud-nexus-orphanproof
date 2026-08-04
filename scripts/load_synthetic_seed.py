#!/usr/bin/env python3
"""Load or verify the synthetic persistent-memory seed with psql."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from apply_database_migrations import (
    ENV_PATH,
    PGSSLROOTCERT,
    MigrationConfigError,
    database_url_to_pg_env,
    find_psql,
    load_database_url,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SEED_SQL = REPO_ROOT / "db" / "seeds" / "001_synthetic_memory_seed.sql"
VERIFICATION_SQL = REPO_ROOT / "db" / "verification" / "002_verify_synthetic_seed.sql"
COMMANDS = {
    "load": SEED_SQL,
    "verify": VERIFICATION_SQL,
}


def fail(message: str, code: int = 1) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(code)


def run_sql(command: str, sql_path: Path) -> int:
    if not sql_path.exists():
        raise MigrationConfigError(f"SQL file is missing for {command}")
    if not PGSSLROOTCERT.exists():
        raise MigrationConfigError("CockroachDB CA certificate is missing")

    database_url = load_database_url(ENV_PATH)
    pg_env = database_url_to_pg_env(database_url)
    psql = find_psql()

    env = os.environ.copy()
    env.update(pg_env)
    env.update(
        {
            "PSQL_PAGER": "cat",
            "PAGER": "cat",
        }
    )

    if command == "load":
        print("starting synthetic seed load", flush=True)
    else:
        print("starting synthetic seed verify", flush=True)

    result = subprocess.run(
        [psql, "-X", "-v", "ON_ERROR_STOP=1", "-P", "pager=off", "-f", str(sql_path)],
        env=env,
        check=False,
    )

    if result.returncode == 0:
        if command == "load":
            print("synthetic seed load completed successfully", flush=True)
        else:
            print("synthetic seed verify completed successfully", flush=True)
    else:
        print(f"synthetic seed {command} failed", file=sys.stderr, flush=True)
    return result.returncode


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in COMMANDS:
        fail("usage: python3 scripts/load_synthetic_seed.py {load|verify}", 2)

    command = argv[1]
    try:
        return run_sql(command, COMMANDS[command])
    except MigrationConfigError as exc:
        fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
