from __future__ import annotations

import structlog

from viraldy.shared.domain.events import DomainEvent

logger = structlog.get_logger(__name__)


class InternalEventPublisher:
    async def publish(self, event: DomainEvent) -> None:
        logger.info(
            "domain_event_published", event_name=event.event_name, event_id=str(event.event_id)
        )
