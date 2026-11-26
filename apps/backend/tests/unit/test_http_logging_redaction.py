from __future__ import annotations

import io
import json
import logging
from collections.abc import Iterator

import httpx
import pytest
import structlog
from celery.signals import after_setup_logger, after_setup_task_logger

from viraldy.platform.config.settings import AppEnv, Settings
from viraldy.platform.observability.logging import configure_logging


@pytest.fixture
def log_output(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[io.StringIO, logging.Handler]]:
    output = io.StringIO()
    handler = logging.StreamHandler(output)
    handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    monkeypatch.setattr(logging.getLogger(), "handlers", [handler])
    previous_levels = {
        logger: logger.level
        for logger in (
            logging.getLogger(),
            logging.getLogger("httpx"),
            logging.getLogger("httpcore"),
        )
    }
    for logger in previous_levels:
        logger.setLevel(logging.INFO)
    previous_config = structlog.get_config()
    yield output, handler
    structlog.configure(**previous_config)
    for logger, level in previous_levels.items():
        logger.setLevel(level)


@pytest.mark.parametrize("entrypoint", ["api", "worker", "task"])
def test_http_request_logs_redact_query_and_preserve_diagnostics(
    entrypoint: str,
    log_output: tuple[io.StringIO, logging.Handler],
) -> None:
    output, handler = log_output
    previous_handlers = list(logging.getLogger().handlers)
    if entrypoint == "api":
        configure_logging(Settings.model_construct(app_env=AppEnv.TEST, log_level="INFO"))
        logging.getLogger("httpx").setLevel(logging.INFO)
    else:
        # Importing the app must register filters for handlers Celery creates later.
        from viraldy.worker.celery_app import celery_app

        signal = after_setup_logger if entrypoint == "worker" else after_setup_task_logger
        for _ in range(2):
            results = signal.send(sender=celery_app, logger=logging.getLogger())
            assert not any(isinstance(result, BaseException) for _, result in results)

    assert logging.getLogger().handlers == previous_handlers
    assert logging.getLogger().level == logging.INFO
    assert handler.level == logging.NOTSET
    transport = httpx.MockTransport(lambda request: httpx.Response(200, request=request))
    with httpx.Client(transport=transport) as client:
        response = client.post(
            "https://provider.invalid/v1/models/example:generate",
            params={"key": "synthetic-credential", "alt": "json"},
        )
    assert response.status_code == 200
    assert output.getvalue() == (
        "INFO HTTP Request: POST https://provider.invalid/v1/models/example:generate"
        '?[REDACTED] "HTTP/1.1 200 OK"\n'
    )
    assert len(handler.filters) == 1


def test_exception_urls_are_redacted_without_changing_original_record(
    log_output: tuple[io.StringIO, logging.Handler],
) -> None:
    output, handler = log_output
    configure_logging(Settings.model_construct(app_env=AppEnv.TEST, log_level="INFO"))
    try:
        raise httpx.ConnectError(
            "Request failed for https://provider.invalid/run?token=example-value"
        )
    except httpx.ConnectError:
        logging.getLogger("provider").exception("Provider request failed")

    rendered = output.getvalue()
    assert "example-value" not in rendered
    assert "httpx.ConnectError" in rendered
    assert "https://provider.invalid/run?[REDACTED]" in rendered
    record = logging.makeLogRecord(
        {"msg": "Request %s", "args": (httpx.URL("https://provider.invalid/run?key=example"),)}
    )
    original_message = record.getMessage()
    sanitized = handler.filters[0].filter(record)
    assert isinstance(sanitized, logging.LogRecord)
    assert sanitized.getMessage() == "Request https://provider.invalid/run?[REDACTED]"
    assert record.getMessage() == original_message


def test_logs_without_url_queries_are_preserved(
    log_output: tuple[io.StringIO, logging.Handler],
) -> None:
    output, _ = log_output
    configure_logging(Settings.model_construct(app_env=AppEnv.TEST, log_level="INFO"))
    logging.getLogger("provider").warning("Retry %s for https://provider.invalid/run", 2)
    assert output.getvalue() == "WARNING Retry 2 for https://provider.invalid/run\n"


def test_json_log_output_preserves_escaping_when_redacting_urls(
    log_output: tuple[io.StringIO, logging.Handler],
) -> None:
    output, _ = log_output
    configure_logging(Settings.model_construct(app_env=AppEnv.PRODUCTION, log_level="INFO"))
    structlog.get_logger("provider").warning(
        'Retry "HTTPS://provider.invalid/run?custom_signature=example-value"',
        request_url="https://provider.invalid/run?label=café&key=example-value",
        unicode_path="https://provider.invalid/café?key=example-value",
        backslash_url="https://provider.invalid/run?key=example-value\\",
        retry=2,
    )
    rendered = json.loads(output.getvalue().removeprefix("WARNING "))
    assert rendered["event"] == 'Retry "HTTPS://provider.invalid/run?[REDACTED]"'
    assert rendered["request_url"] == "https://provider.invalid/run?[REDACTED]"
    assert rendered["unicode_path"] == "https://provider.invalid/café?[REDACTED]"
    assert rendered["backslash_url"] == "https://provider.invalid/run?[REDACTED]"
    assert rendered["retry"] == 2


def test_preformatted_exception_and_stack_urls_are_redacted(
    log_output: tuple[io.StringIO, logging.Handler],
) -> None:
    output, handler = log_output
    configure_logging(Settings.model_construct(app_env=AppEnv.TEST, log_level="INFO"))
    record = logging.makeLogRecord(
        {
            "msg": "Provider failure",
            "args": (),
            "levelno": logging.ERROR,
            "exc_text": "Failure https://provider.invalid/run?key=example-value",
            "stack_info": "Stack https://provider.invalid/run?signature=example-value",
        }
    )
    handler.handle(record)
    assert "example-value" not in output.getvalue()
    assert output.getvalue().count("?[REDACTED]") == 2
    assert record.exc_text is not None and "example-value" in record.exc_text


@pytest.mark.parametrize(
    ("path", "query"),
    [("run", "label=author's&key=example-value"), ("author's", "key=example-value")],
)
def test_httpx_urls_with_apostrophes_cannot_bypass_redaction(
    path: str,
    query: str,
    log_output: tuple[io.StringIO, logging.Handler],
) -> None:
    output, _ = log_output
    configure_logging(Settings.model_construct(app_env=AppEnv.TEST, log_level="INFO"))
    logging.getLogger("httpx").setLevel(logging.INFO)
    transport = httpx.MockTransport(lambda request: httpx.Response(200, request=request))
    with httpx.Client(transport=transport) as client:
        client.get(f"https://provider.invalid/{path}?{query}")
    assert output.getvalue() == (
        f'INFO HTTP Request: GET https://provider.invalid/{path}?[REDACTED] "HTTP/1.1 200 OK"\n'
    )


def test_url_query_redaction_preserves_enclosing_single_quotes(
    log_output: tuple[io.StringIO, logging.Handler],
) -> None:
    output, _ = log_output
    configure_logging(Settings.model_construct(app_env=AppEnv.TEST, log_level="INFO"))
    logging.getLogger("provider").warning(
        "Provider rejected URL '%s'.", "https://provider.invalid/run?key=example-value"
    )
    assert output.getvalue() == (
        "WARNING Provider rejected URL 'https://provider.invalid/run?[REDACTED]'.\n"
    )
