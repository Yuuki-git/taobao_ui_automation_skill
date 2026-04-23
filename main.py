from __future__ import annotations

import logging
from typing import Any, Dict
from uuid import uuid4

from config import configure_logging, get_config
from models import SkillResult, TaskPayload
from modules.error_codes import (
    HUMAN_INTERVENTION_CODES,
    INVALID_INPUT,
    UNKNOWN_ERROR,
    SkillError,
)


CONFIG = get_config()
configure_logging(CONFIG.log_level)
LOGGER = logging.getLogger(__name__)


def _build_orchestrator(config: Any) -> Any:
    """Create orchestrator instance lazily to keep phase-1 dependencies minimal."""

    from modules.orchestrator import Orchestrator

    return Orchestrator(config=config)


def _status_from_error(error_code: str) -> str:
    if error_code in HUMAN_INTERVENTION_CODES:
        return "need_human_intervention"
    return "failed"


def _error_result(
    *,
    error_code: str,
    message: str,
    detail: Dict[str, Any] | None,
    task_status: str,
) -> Dict[str, Any]:
    return SkillResult.from_error(
        error_code=error_code,
        message=message,
        detail=detail,
        task_status=task_status,
    ).to_dict()


def run_skill(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Skill entry point. Validate input, execute flow, and normalize output."""

    task_id = (
        payload.get("task_id")
        if isinstance(payload, dict)
        and isinstance(payload.get("task_id"), str)
        and payload.get("task_id").strip()
        else uuid4().hex
    )
    logger = logging.LoggerAdapter(LOGGER, {"task_id": task_id})

    if not isinstance(payload, dict):
        return _error_result(
            error_code=INVALID_INPUT,
            message="payload must be an object.",
            detail={"payload_type": type(payload).__name__},
            task_status="failed",
        )

    try:
        task_payload = TaskPayload.from_dict(payload)
        logger = logging.LoggerAdapter(LOGGER, {"task_id": task_payload.task_id})

        logger.info("Skill execution started.")
        orchestrator = _build_orchestrator(CONFIG)
        result = orchestrator.run(task_payload)
        if not isinstance(result, SkillResult):
            raise SkillError(
                UNKNOWN_ERROR,
                "Orchestrator returned an unsupported result type.",
                {"result_type": type(result).__name__},
            )

        logger.info("Skill execution completed.")
        return result.to_dict()
    except SkillError as exc:
        logger.warning("Skill execution failed: %s", exc.message)
        return _error_result(
            error_code=exc.code,
            message=exc.message,
            detail=exc.detail,
            task_status=_status_from_error(exc.code),
        )
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.exception("Unhandled exception during skill execution.")
        return _error_result(
            error_code=UNKNOWN_ERROR,
            message="Unexpected error during skill execution.",
            detail={"exception_type": type(exc).__name__, "exception": str(exc)},
            task_status="failed",
        )


if __name__ == "__main__":
    sample_payload = {
        "platform": "taobao",
        "keyword": "蓝牙耳机",
        "constraints": {"positive_rate_gte": 99},
        "action": "search_only",
        "notify_channel": "feishu",
        "max_candidates": 5,
        "need_login": True,
    }
    print(run_skill(sample_payload))
