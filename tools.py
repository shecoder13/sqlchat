"""The three tools the agent can call.

The docstrings are not just documentation: the model reads them to decide
when and how to use each tool, so they are written as instructions.
"""
import sqlite3

from langchain_core.tools import tool

import db

_RECOVERABLE = (ValueError, sqlite3.Error, OSError)


@tool
def list_tables() -> str:
    """List every table in the inventory database.
    Call this first whenever you are unsure what data is available."""
    try:
        return ", ".join(db.table_names())
    except _RECOVERABLE as exc:
        return f"Error: {exc}"


@tool
def describe_table(table_name: str) -> str:
    """Show one table's columns, types, foreign keys and 3 sample rows.
    Call this for every table you plan to query, before writing any SQL,
    so you use real column names instead of guessing."""
    try:
        return db.describe_table(table_name)
    except _RECOVERABLE as exc:
        return f"Error: {exc}"


@tool
def run_query(sql: str) -> str:
    """Run ONE read-only SQLite SELECT statement and return the rows (at most 50).
    Only SELECT is allowed; no semicolons, comments or data changes.
    If the result is an error message, read it carefully, fix the SQL and try again."""
    try:
        return db.run_select(sql)
    except _RECOVERABLE as exc:
        return f"Error: {exc}"


TOOLS = [list_tables, describe_table, run_query]
