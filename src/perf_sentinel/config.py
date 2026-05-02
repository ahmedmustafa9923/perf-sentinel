"""Runtime configuration loaded from environment."""
import os
from pathlib import Path
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    db_url: str
    anthropic_api_key: str | None
    artifacts_dir: Path

    @classmethod
    def load(cls) -> "Config":
        return cls(
            db_url=os.getenv("DB_URL", "sqlite:///perf_sentinel.db"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            artifacts_dir=Path(os.getenv("ARTIFACTS_DIR", "artifacts")),
        )


config = Config.load()