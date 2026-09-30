"""Runtime configuration.

Mirrors what BMAD resolves from ``_bmad/_config/*.toml`` at agent activation
(``modules.bmm.planning_artifacts`` / ``modules.bmm.project_knowledge``) — here
it is plain environment variables so the graph has no hidden install step.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    model: str = os.environ.get("BMAD_MODEL", "anthropic:claude-sonnet-5")
    output_dir: str = os.environ.get("BMAD_OUTPUT_DIR", "./_bmad-output")
    review_loop_cap: int = int(os.environ.get("BMAD_REVIEW_LOOP_CAP", "5"))
    recursion_limit: int = int(os.environ.get("BMAD_RECURSION_LIMIT", "50"))


settings = Settings()
