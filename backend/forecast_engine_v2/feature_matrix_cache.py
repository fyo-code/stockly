"""Small on-disk cache helpers for forecast v2 feature matrices."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

try:
    from .feature_matrix import build_feature_matrix
    from .scorecard import ScorecardConfig
except ImportError:  # Allows direct script execution.
    from feature_matrix import build_feature_matrix
    from scorecard import ScorecardConfig


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CACHE_DIR = PROJECT_ROOT / "backend" / "data" / "forecast_v2_feature_cache"
CACHE_VERSION = "feature_matrix_cache_v2_2026_05_26_discount_hygiene"


def _db_fingerprint(conn: sqlite3.Connection) -> dict[str, object]:
    db_path = conn.execute("PRAGMA database_list").fetchall()[0][2]
    path = Path(db_path).resolve() if db_path else Path(":memory:")
    stat = path.stat() if path.exists() else None
    schema_version = conn.execute("PRAGMA schema_version").fetchone()[0]
    user_version = conn.execute("PRAGMA user_version").fetchone()[0]
    return {
        "db_path": str(path),
        "db_size": None if stat is None else int(stat.st_size),
        "db_mtime_ns": None if stat is None else int(stat.st_mtime_ns),
        "schema_version": int(schema_version),
        "user_version": int(user_version),
    }


def _config_fingerprint(config: ScorecardConfig | None) -> dict[str, object]:
    config = config or ScorecardConfig()
    return {
        "horizon_weeks": int(config.horizon_weeks),
        "material_units_threshold": float(config.material_units_threshold),
        "phantom_threshold": float(config.phantom_threshold),
        "sale_threshold": float(config.sale_threshold),
    }


def _cache_payload(
    conn: sqlite3.Connection,
    target_starts: list[str],
    population: str,
    revenue_rank_limit: int | None,
    config: ScorecardConfig | None,
) -> dict[str, object]:
    return {
        "version": CACHE_VERSION,
        "target_starts": sorted(target_starts),
        "population": population,
        "revenue_rank_limit": revenue_rank_limit,
        "scorecard_config": _config_fingerprint(config),
        "db": _db_fingerprint(conn),
    }


def _cache_path(
    payload: dict[str, object],
    population: str,
    revenue_rank_limit: int | None,
    cache_dir: Path = DEFAULT_CACHE_DIR,
) -> Path:
    digest = hashlib.sha1(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    rank_label = "all" if revenue_rank_limit is None else f"top{revenue_rank_limit}"
    return cache_dir / f"feature_matrix_{population}_{rank_label}_{digest}.pkl"


def load_or_build_feature_matrix(
    conn: sqlite3.Connection,
    target_starts: list[str],
    population: str,
    config: ScorecardConfig | None = None,
    revenue_rank_limit: int | None = None,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    refresh: bool = False,
) -> tuple[pd.DataFrame, Path, bool]:
    """Return a feature matrix, using a pickle cache when available.

    The cache is intentionally boring: it is keyed by target windows,
    population, revenue rank limit, and a manual cache version. Refresh it when
    feature code changes materially.
    """

    cache_dir.mkdir(parents=True, exist_ok=True)
    payload = _cache_payload(conn, target_starts, population, revenue_rank_limit, config)
    path = _cache_path(payload, population, revenue_rank_limit, cache_dir=cache_dir)
    meta_path = path.with_suffix(".json")
    if path.exists() and not refresh:
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if meta.get("cache_key") == payload:
                return pd.read_pickle(path), path, True
        stale_path = path.with_suffix(f".stale-{os.getpid()}.pkl")
        path.rename(stale_path)

    matrix = build_feature_matrix(
        conn,
        target_starts=target_starts,
        population=population,
        config=config,
        revenue_rank_limit=revenue_rank_limit,
    )
    matrix.to_pickle(path)
    meta = {
        "cache_key": payload,
        "cache_version": CACHE_VERSION,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "rows": int(len(matrix)),
        "columns": int(len(matrix.columns)),
        "target_starts": sorted(target_starts),
        "population": population,
        "revenue_rank_limit": revenue_rank_limit,
    }
    meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8")
    return matrix, path, False
