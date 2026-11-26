from __future__ import annotations

import logging
import re
import sys

import structlog

from viraldy.platform.config.settings import AppEnv, Settings

_HTTP_URL_QUERY = re.compile(
    r"""(https?://[^\s"<>?]+)\?((?:\\[^\s"<>]|[^\\\s"<>])*)""", re.IGNORECASE
)


def _redact_http_url_query(match: re.Match[str]) -> str:
    closing_quote = re.search(r"('[.,;:)\]}]*)$", match.group(2))
    suffix = closing_quote.group(0) if closing_quote else ""
    return f"{match.group(1)}?[REDACTED]{suffix}"


class HttpUrlQueryRedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> logging.LogRecord:
        message = record.getMessage()
        redacted_message = _HTTP_URL_QUERY.sub(_redact_http_url_query, message)
        exception = record.exc_text
        if record.exc_info and not exception:
            exception = logging.Formatter().formatException(record.exc_info)
        redacted_exception = (
            _HTTP_URL_QUERY.sub(_redact_http_url_query, exception) if exception else exception
        )
        redacted_stack = (
            _HTTP_URL_QUERY.sub(_redact_http_url_query, record.stack_info)
            if record.stack_info
            else record.stack_info
        )
        if (
            redacted_message == message
            and redacted_exception == exception
            and redacted_stack == record.stack_info
        ):
            return record
        return logging.makeLogRecord(
            {
                **record.__dict__,
                "msg": redacted_message,
                "args": (),
                "exc_info": None,
                "exc_text": redacted_exception,
                "stack_info": redacted_stack,
            }
        )


def configure_http_log_redaction(logger: logging.Logger, **_: object) -> None:
    # Provider query keys are not standardized, so redact every HTTP(S) query.
    for handler in logger.handlers:
        if not any(isinstance(item, HttpUrlQueryRedactionFilter) for item in handler.filters):
            handler.addFilter(HttpUrlQueryRedactionFilter())


def configure_logging(settings: Settings) -> None:
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    processors: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    if settings.app_env in {AppEnv.LOCAL, AppEnv.TEST}:
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
    )
    configure_http_log_redaction(logging.getLogger())
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
