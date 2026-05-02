"""Perf Sentinel — AI-powered CI performance observability."""
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from .db import init_db, connect
from .ingest import ingest_pytest_benchmark


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Perf Sentinel", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


class IngestResponse(BaseModel):
    run_id: str
    benchmark_count: int


@app.post("/ingest", response_model=IngestResponse)
async def ingest(
    artifact: UploadFile = File(...),
    target: str = Form(...),
    commit_sha: str | None = Form(None),
    branch: str | None = Form(None),
    ci_url: str | None = Form(None),
):
    tmp = Path("artifacts") / f"_upload_{artifact.filename}"
    tmp.parent.mkdir(exist_ok=True)
    tmp.write_bytes(await artifact.read())

    run_id = ingest_pytest_benchmark(
        tmp,
        target=target,
        commit_sha=commit_sha,
        branch=branch,
        ci_url=ci_url,
    )
    with connect() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM benchmarks WHERE run_id = ?",
            (run_id,),
        ).fetchone()[0]
    return IngestResponse(run_id=run_id, benchmark_count=count)


@app.get("/runs")
def list_runs(target: str | None = None, limit: int = 20):
    with connect() as conn:
        if target:
            rows = conn.execute(
                "SELECT * FROM runs WHERE target = ? "
                "ORDER BY started_at DESC LIMIT ?",
                (target, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM runs ORDER BY started_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [dict(r) for r in rows]


@app.get("/runs/{run_id}")
def get_run(run_id: str):
    with connect() as conn:
        run = conn.execute(
            "SELECT * FROM runs WHERE id = ?", (run_id,)
        ).fetchone()
        if not run:
            raise HTTPException(status_code=404, detail="run not found")
        benchmarks = conn.execute(
            "SELECT * FROM benchmarks WHERE run_id = ?", (run_id,)
        ).fetchall()
    return {"run": dict(run), "benchmarks": [dict(b) for b in benchmarks]}