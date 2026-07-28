from __future__ import annotations

import sentry_sdk

from viraldy.platform.config.settings import Settings


def configure_sentry(settings: Settings) -> None:
    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn.get_secret_value(),
            environment=settings.app_env,
            release=settings.release_version,
        )
