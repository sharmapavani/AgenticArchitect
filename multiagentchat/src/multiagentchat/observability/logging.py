"""Structured logging filter injecting correlation ids."""

from __future__ import annotations

import logging

from multiagentchat.observability.context import get_run_id, get_session_id, run_id_to_trace_id


class CorrelationFilter(logging.Filter):
    """Inject run_id, session_id, trace_id into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        run_id = get_run_id()
        session_id = get_session_id()
        record.run_id = run_id or "-"
        record.session_id = session_id or "-"
        record.trace_id = run_id_to_trace_id(run_id) if run_id else "-"
        return True


def install_correlation_logging() -> None:
    root = logging.getLogger()
    correlation_filter = CorrelationFilter()
    for handler in root.handlers:
        if not any(isinstance(f, CorrelationFilter) for f in handler.filters):
            handler.addFilter(correlation_filter)
    fmt = (
        "%(asctime)s %(levelname)s [%(name)s] "
        "run_id=%(run_id)s session_id=%(session_id)s trace_id=%(trace_id)s "
        "%(message)s"
    )
    for handler in root.handlers:
        handler.setFormatter(logging.Formatter(fmt))
