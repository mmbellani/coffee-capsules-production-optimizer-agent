"""DuckDB access layer + analytics-query registry for the dashboard."""
from __future__ import annotations
import re
from functools import lru_cache
from pathlib import Path

import duckdb
import pandas as pd

import config


def substitute(sql: str) -> str:
    """Replace {TOKEN} placeholders from config.SQL_SUBSTITUTIONS."""
    for key, val in config.SQL_SUBSTITUTIONS.items():
        sql = sql.replace("{" + key + "}", str(val))
    return sql


def connect(read_only: bool = True) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(str(config.DB_PATH), read_only=read_only)
    con.execute("PRAGMA threads=4")
    return con


def _parse_header(sql: str) -> dict:
    meta = {"title": None, "category": "Other", "description": ""}
    desc_lines = []
    for line in sql.splitlines():
        m = re.match(r"--\s*title:\s*(.+)", line)
        if m:
            meta["title"] = m.group(1).strip(); continue
        m = re.match(r"--\s*category:\s*(.+)", line)
        if m:
            meta["category"] = m.group(1).strip(); continue
        m = re.match(r"--\s*description:\s*(.+)", line)
        if m:
            desc_lines.append(m.group(1).strip()); continue
        if desc_lines and re.match(r"--\s{2,}\S", line):  # continuation of description
            desc_lines.append(line.lstrip("- ").strip()); continue
        if not line.startswith("--"):
            break
    meta["description"] = " ".join(desc_lines)
    return meta


@lru_cache(maxsize=1)
def registry() -> dict:
    """Discover analytics SQL files -> {id: {title, category, description, path, sql}}."""
    reg = {}
    for path in sorted(config.ANALYTICS_DIR.glob("*.sql")):
        raw = path.read_text(encoding="utf-8")
        meta = _parse_header(raw)
        reg[path.stem] = {
            "id": path.stem,
            "title": meta["title"] or path.stem,
            "category": meta["category"],
            "description": meta["description"],
            "path": str(path),
            "sql": substitute(raw),
        }
    return reg


def run_query(query_id: str) -> pd.DataFrame:
    reg = registry()
    if query_id not in reg:
        raise KeyError(f"Unknown query '{query_id}'")
    con = connect(read_only=True)
    try:
        return con.execute(reg[query_id]["sql"]).df()
    finally:
        con.close()


def run_sql(sql: str) -> pd.DataFrame:
    """Run arbitrary (read-only) SQL for the SQL Explorer tab."""
    con = connect(read_only=True)
    try:
        return con.execute(substitute(sql)).df()
    finally:
        con.close()


def dim_machine() -> pd.DataFrame:
    return run_sql("SELECT * FROM dim_machine ORDER BY machine_id")
