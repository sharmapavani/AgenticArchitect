"""CLI to initialize the SQLite chat audit database."""

from __future__ import annotations

import argparse
from pathlib import Path

from multiagentchat.audit.sqlite_db import get_db_path, init_db


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize chat audit SQLite database")
    parser.add_argument(
        "--db-path",
        default=None,
        help="Override CHAT_AUDIT_DB_PATH (default: ./data/chat_audit.db)",
    )
    args = parser.parse_args()
    path = init_db(Path(args.db_path) if args.db_path else None)
    print(f"Chat audit database ready at {path}")


if __name__ == "__main__":
    main()
