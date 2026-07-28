from __future__ import annotations


class DisabledModelGateway:
    async def transcribe_audio(self, asset_id: str) -> None:
        return None

    async def extract_visual_evidence(self, asset_id: str) -> None:
        return None

    async def extract_text_overlay(self, asset_id: str) -> None:
        return None

    async def classify_creative_elements(self, asset_id: str) -> None:
        return None

    async def generate_campaign_pack(self, product_id: str) -> None:
        return None

    async def evaluate_preflight(self, asset_id: str) -> None:
        return None

    async def generate_revision_message(self, asset_id: str) -> None:
        return None

    async def embed_content(self, content_id: str) -> None:
        return None
