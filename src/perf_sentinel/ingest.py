"""Parse pytest-benchmark JSON artifacts into our DB schema."""
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

from .db import connect


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

    with connect() as conn:
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
                conn.execute(
                    "INSERT INTO benchmarks (run_id, name, metric, value, unit) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (run_id, b["fullname"], metric, value, unit),
                )

    return run_id