"""Read-only SQLite access with guardrails for LLM-generated SQL.

Three layers of protection:
  1. The database file is opened read-only, so writes fail at the SQLite level.
  2. Only a single SELECT (or WITH ... SELECT) statement passes validation.
  3. Results are capped at MAX_ROWS so a careless query can't flood the model.
"""
import os
import re
import sqlite3
from pathlib import Path

MAX_ROWS = 50

_BLOCKED = re.compile(
    r"\b(insert|update|delete|drop|alter|create|replace|attach|detach|pragma|vacuum|reindex)\b",
    re.IGNORECASE,
)


def db_path() -> Path:
    """Database file: DB_PATH from the environment, else inventory.db next to this file."""
    return Path(os.getenv("DB_PATH") or Path(__file__).with_name("inventory.db"))


def get_connection() -> sqlite3.Connection:
    path = db_path()
    if not path.exists():
        raise FileNotFoundError(f"Database not found at {path}. Run `python seed_db.py` first.")
    return sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)


def validate_select(sql: str) -> str:
    """Return the cleaned SQL, or raise ValueError explaining why it was rejected."""
    cleaned = sql.strip().rstrip(";").strip()
    if not cleaned:
        raise ValueError("Empty query.")
    if ";" in cleaned:
        raise ValueError("Only one statement is allowed.")
    if "--" in cleaned or "/*" in cleaned:
        raise ValueError("SQL comments are not allowed.")
    if not re.match(r"(?is)^(select|with)\b", cleaned):
        raise ValueError("Only SELECT queries are allowed.")
    hit = _BLOCKED.search(cleaned)
    if hit:
        raise ValueError(f"Keyword '{hit.group(0)}' is not allowed in read-only queries.")
    return cleaned


def _format_table(columns: list[str], rows: list[tuple]) -> str:
    def cell(value) -> str:
        return "NULL" if value is None else str(value)

    lines = [" | ".join(columns), " | ".join("---" for _ in columns)]
    lines += [" | ".join(cell(v) for v in row) for row in rows]
    return "\n".join(lines)


def run_select(sql: str) -> str:
    """Validate and run one SELECT, returning a text table (max MAX_ROWS rows)."""
    cleaned = validate_select(sql)
    conn = get_connection()
    try:
        cursor = conn.execute(cleaned)
        rows = cursor.fetchmany(MAX_ROWS + 1)
        columns = [d[0] for d in cursor.description or []]
    finally:
        conn.close()

    if not rows:
        return "Query ran successfully but returned no rows."

    truncated = len(rows) > MAX_ROWS
    text = _format_table(columns, rows[:MAX_ROWS])
    if truncated:
        text += f"\n(Showing the first {MAX_ROWS} rows; more exist. Add a tighter WHERE or aggregate.)"
    return text


def table_names() -> list[str]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    finally:
        conn.close()
    return [r[0] for r in rows]


def describe_table(name: str) -> str:
    """Columns, foreign keys and 3 sample rows for one table."""
    available = table_names()
    if name not in available:  # also keeps the name safe to interpolate below
        raise ValueError(f"Unknown table '{name}'. Available tables: {', '.join(available)}")

    conn = get_connection()
    try:
        columns = conn.execute(f'PRAGMA table_info("{name}")').fetchall()
        foreign_keys = conn.execute(f'PRAGMA foreign_key_list("{name}")').fetchall()
        sample = conn.execute(f'SELECT * FROM "{name}" LIMIT 3')
        sample_rows = sample.fetchall()
        sample_columns = [d[0] for d in sample.description]
    finally:
        conn.close()

    lines = [f"Table: {name}", "Columns:"]
    for _cid, col, col_type, notnull, _default, pk in columns:
        flags = (" PRIMARY KEY" if pk else "") + (" NOT NULL" if notnull else "")
        lines.append(f"  - {col} {col_type}{flags}")
    if foreign_keys:
        lines.append("Foreign keys:")
        for fk in foreign_keys:
            lines.append(f"  - {fk[3]} -> {fk[2]}.{fk[4]}")
    lines.append("Sample rows:")
    lines.append(_format_table(sample_columns, sample_rows) if sample_rows else "  (table is empty)")
    return "\n".join(lines)
