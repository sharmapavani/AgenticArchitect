"""End-to-end request timing for CAIChatFlow + crew pipeline."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from time import perf_counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from multiagentchat.utils.crew_timing import TaskTimingRecord

logger = logging.getLogger("multiagentchat.request")


@dataclass
class StepTimingRecord:
    phase: str
    label: str
    duration_s: float
    cumulative_s: float
    detail: str = ""


@dataclass
class RequestTimingTracker:
    """Tracks flow steps and nested crew task durations for one /chat request."""

    run_id: str = ""
    session_id: str = ""
    message_preview: str = ""
    _started: float = field(default=0.0, repr=False)
    _last_mark: float = field(default=0.0, repr=False)
    steps: list[StepTimingRecord] = field(default_factory=list)

    def start(self) -> None:
        self._started = perf_counter()
        self._last_mark = self._started

    def end_step(self, label: str, phase: str = "flow", detail: str = "") -> None:
        now = perf_counter()
        if self._started == 0.0:
            self.start()
        duration = now - self._last_mark
        cumulative = now - self._started
        self._last_mark = now
        self.steps.append(
            StepTimingRecord(
                phase=phase,
                label=label,
                duration_s=duration,
                cumulative_s=cumulative,
                detail=detail,
            )
        )

    def add_crew_steps(self, crew_records: list[TaskTimingRecord]) -> None:
        """Append crew task timings (durations relative to crew kickoff)."""
        for rec in crew_records:
            detail = rec.agent
            if rec.raw_chars:
                detail = f"{rec.agent} ({rec.raw_chars} chars)"
            self.steps.append(
                StepTimingRecord(
                    phase="crew",
                    label=rec.label,
                    duration_s=rec.duration_s,
                    cumulative_s=rec.cumulative_s,
                    detail=detail,
                )
            )

    def log_request_summary(self, path: str) -> None:
        """Log unified timing table when the chat response is ready."""
        total = perf_counter() - self._started if self._started else 0.0
        preview = self.message_preview[:60].replace("\n", " ")

        logger.info("=" * 72)
        logger.info(
            "REQUEST COMPLETE run_id=%s session_id=%s path=%s total=%.2fs message=%r",
            self.run_id,
            self.session_id,
            path,
            total,
            preview,
        )
        logger.info("-" * 72)
        logger.info("  #   phase   step                           duration   cumulative")
        logger.info("-" * 72)

        for index, step in enumerate(self.steps, start=1):
            detail_suffix = f"  ({step.detail})" if step.detail else ""
            if step.phase == "crew":
                logger.info(
                    "  %02d   crew    %-28s %7.2fs   (crew +%.2fs)%s",
                    index,
                    step.label,
                    step.duration_s,
                    step.cumulative_s,
                    detail_suffix,
                )
            else:
                logger.info(
                    "  %02d   flow    %-28s %7.2fs   %7.2fs%s",
                    index,
                    step.label,
                    step.duration_s,
                    step.cumulative_s,
                    detail_suffix,
                )

        logger.info("-" * 72)
        logger.info(
            "  TOTAL %-58s %7.2fs",
            "",
            total,
        )
        logger.info("=" * 72)
