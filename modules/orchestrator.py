from __future__ import annotations

from typing import Any

from models import SkillResult, TaskPayload
from modules.error_codes import SkillError, UNKNOWN_ERROR


class Orchestrator:
    """Main flow coordinator.

    TODO(phase-2): implement browser lifecycle, authentication, search, and action flow.
    """

    def __init__(self, config: Any) -> None:
        self.config = config

    def run(self, payload: TaskPayload) -> SkillResult:
        """Execute the end-to-end task flow.

        TODO(phase-2): replace placeholder with real orchestration logic.
        """

        raise SkillError(
            UNKNOWN_ERROR,
            "Orchestrator flow is not implemented yet (phase-2).",
            {"phase": "phase-2", "action": payload.action},
        )
