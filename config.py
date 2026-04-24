from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_STORAGE_STATE_PATH = BASE_DIR / "storage" / "taobao_storage_state.json"


class _TaskIdFilter(logging.Filter):
    """Inject a default task_id into log records when it is missing."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "task_id"):
            record.task_id = "-"
        return True


@dataclass(frozen=True)
class SkillConfig:
    """Runtime settings for the Taobao automation skill."""

    default_platform: str = "taobao"
    default_notify_channel: str = "feishu"
    default_max_candidates: int = 5
    default_need_login: bool = True
    default_headless: bool = False
    default_timeout_ms: int = 15000
    taobao_home_url: str = "https://www.taobao.com"
    storage_state_path: Path = DEFAULT_STORAGE_STATE_PATH
    enable_stealth: bool = False
    log_level: str = "INFO"


def get_config() -> SkillConfig:
    """Load configuration from environment variables with safe defaults."""

    return SkillConfig(
        default_platform=os.getenv("SKILL_DEFAULT_PLATFORM", "taobao"),
        default_notify_channel=os.getenv("SKILL_DEFAULT_NOTIFY_CHANNEL", "feishu"),
        default_max_candidates=int(os.getenv("SKILL_DEFAULT_MAX_CANDIDATES", "5")),
        default_need_login=os.getenv("SKILL_DEFAULT_NEED_LOGIN", "true").lower()
        == "true",
        default_headless=os.getenv("SKILL_HEADLESS", "false").lower() == "true",
        default_timeout_ms=int(os.getenv("SKILL_TIMEOUT_MS", "15000")),
        taobao_home_url=os.getenv("SKILL_TAOBAO_HOME_URL", "https://www.taobao.com"),
        storage_state_path=Path(
            os.getenv("SKILL_STORAGE_STATE_PATH", str(DEFAULT_STORAGE_STATE_PATH))
        ),
        # TODO(phase-2): optional flag only. Stealth plugin is not required dependency.
        enable_stealth=os.getenv("SKILL_ENABLE_STEALTH", "false").lower() == "true",
        log_level=os.getenv("SKILL_LOG_LEVEL", "INFO").upper(),
    )


def configure_logging(log_level: str) -> None:
    """Configure process-level logging once with task_id context support."""

    root_logger = logging.getLogger()
    if root_logger.handlers:
        for handler in root_logger.handlers:
            handler.addFilter(_TaskIdFilter())
        return

    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s %(levelname)s [task_id=%(task_id)s] %(name)s - %(message)s",
    )
    for handler in root_logger.handlers:
        handler.addFilter(_TaskIdFilter())
