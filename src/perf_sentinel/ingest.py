"""Parse pytest-benchmark JSON artifacts into our DB schema."""
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

from .db import connect


REGRESSION_THRESHOLD_PCT = 10.0  # >10% slower = regressed


def _find_baseline_value(conn, target: str, name: str, metric: str) -> float | None:
    """
    Return the most recent prior value on the main branch for this benchmark.
    Returns None if no baseline exists yet (first run for this benchmark).
    """
    row = conn.execute(
        """
        SELECT b.value
        FROM benchmarks b
        JOIN runs r ON r.id = b.run_id
        WHERE r.target = ?
          AND r.branch = 'main'
          AND b.name = ?
          AND b.metric = ?
        ORDER BY r.started_at DESC
        LIMIT 1
        """,
        (target, name, metric),
    ).fetchone()
    return row["value"] if row else None


def ingest_pytest_benchmark(
    artifact_path: str | Path,
    *,
    target: str,
    commit_sha: str | None = None,
    branch: str | None = None,
    ci_url: str | None = None,
) -> str:
    artifact = Path(artifact_path).read_text()
    data: dict[str, Any] = json.loads(artifact)

    run_id = f"run-{uuid.uuid4().hex[:12]}"
    started_at = datetime.fromisoformat(data["datetime"]).replace(
        tzinfo=timezone.utc
    ).isoformat()

    benchmarks = data.get("benchmarks", [])
    duration = sum(b["stats"]["total"] for b in benchmarks) if benchmarks else 0.0

    # We'll determine status as we walk the benchmarks.
    has_regression = False

    with connect() as conn:
        # Insert run with placeholder status; we'll update at the end.
        conn.execute(
            """
            INSERT INTO runs (id, target, commit_sha, branch, started_at,
                              duration_seconds, status, ci_url, raw_artifact)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (run_id, target, commit_sha, branch, started_at,
             duration, "passed", ci_url, artifact),
        )

        for b in benchmarks:
            stats = b["stats"]
            for metric, value, unit in [
                ("latency_p50_ms", stats["median"] * 1000, "ms"),
                ("latency_max_ms", stats["max"] * 1000, "ms"),
                ("ops_per_sec",    stats["ops"],          "rps"),
            ]:
                # Look up baseline on main for this benchmark.
                baseline = _find_baseline_value(conn, target, b["fullname"], metric)
                delta_pct = None
                if baseline is not None and baseline > 0:
                    if metric == "ops_per_sec":
                        # For throughput, lower is worse.
                        delta_pct = (baseline - value) / baseline * 100
                    else:
                        # For latency, higher is worse.
                        delta_pct = (value - baseline) / baseline * 100
                    if delta_pct > REGRESSION_THRESHOLD_PCT:
                        has_regression = True

                conn.execute(
                    """
                    INSERT INTO benchmarks
                        (run_id, name, metric, value, unit, baseline, delta_pct)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (run_id, b["fullname"], metric, value, unit, baseline, delta_pct),
                )

        # Update run status if regressions found.
        if has_regression:
            conn.execute(
                "UPDATE runs SET status = 'regressed' WHERE id = ?",
                (run_id,),
            )

    return run_id