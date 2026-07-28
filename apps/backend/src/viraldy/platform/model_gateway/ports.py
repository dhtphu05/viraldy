from __future__ import annotations

from typing import Protocol


class ModelGatewayPort(Protocol):
    async def transcribe_audio(self, asset_id: str) -> None:
        raise NotImplementedError

    async def extract_visual_evidence(self, asset_id: str) -> None:
        raise NotImplementedError

    async def extract_text_overlay(self, asset_id: str) -> None:
        raise NotImplementedError

    async def classify_creative_elements(self, asset_id: str) -> None:
        raise NotImplementedError

    async def generate_campaign_pack(self, product_id: str) -> None:
        raise NotImplementedError

    async def evaluate_preflight(self, asset_id: str) -> None:
        raise NotImplementedError

    async def generate_revision_message(self, asset_id: str) -> None:
        raise NotImplementedError

    async def embed_content(self, content_id: str) -> None:
        raise NotImplementedError
