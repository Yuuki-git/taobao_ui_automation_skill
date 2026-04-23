from __future__ import annotations

import logging
from typing import Any, Optional

from models import SkillResult


class Notifier:
    """Notification adapter with log-only behavior for the current phase."""

    def __init__(self, *, task_id: str | None = None) -> None:
        self._logger = logging.LoggerAdapter(
            logging.getLogger(__name__), {"task_id": task_id or "-"}
        )

    def notify_success(self, result: SkillResult) -> None:
        """Log successful execution details.

        TODO(phase-3): integrate with external channels such as Feishu webhook.
        """

        product_title = result.selected_product.title if result.selected_product else None
        self._logger.info(
            "Notify success: status=%s, product=%s",
            result.task_status,
            product_title,
        )

    def notify_failure(
        self, error_code: str, message: str, detail: Optional[dict[str, Any]] = None
    ) -> None:
        """Log failed execution details.

        TODO(phase-3): integrate with external channels such as Feishu webhook.
        """

        self._logger.warning(
            "Notify failure: error_code=%s, message=%s, detail=%s",
            error_code,
            message,
            detail,
        )
