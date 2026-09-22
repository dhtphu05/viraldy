import re
from typing import Any, Protocol

from .errors import SmartRemakeError, SmartRemakeValidationError
from .guards import assert_allowed_request_type, assert_no_reference_video_in_render_payload
from .media_validation import assert_product_image
from .schemas import UploadedMedia


class SmartRemakeFlowKit(Protocol):
    async def check_health(self) -> dict[str, Any]:
        ...

    async def check_google_flow_auth(self) -> None:
        ...

    async def create_project(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...

    async def upload_product_image(self, *, bytes_data: bytes, mime_type: str, project_id: str, file_name: str) -> dict[str, Any]:
        ...

    async def list_project_characters(self, project_id: str) -> list[dict[str, Any]]:
        ...

    async def update_project_character(self, project_id: str, character_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        ...

    async def create_video(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...

    async def create_scene(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...

    async def create_batch_requests(self, payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
        ...

    async def get_request_status(self, request_id: str) -> dict[str, Any]:
        ...


def normalize_project_name(value: str, fallback: str = "Smart Remake") -> str:
    normalized = re.sub(r"\s+", " ", re.sub(r"[\x00-\x1f\x7f]", " ", value)).strip()
    fallback_name = re.sub(r"\s+", " ", fallback).strip() or "Smart Remake"
    name = normalized or fallback_name
    return name[:64].rsplit(" ", 1)[0] if len(name) > 64 and " " in name[:64] else name[:64]


def _image_filename(media: UploadedMedia) -> str:
    if media.file_name:
        return media.file_name
    if media.mime_type == "image/png":
        return "smart_remake_product_ref.png"
    if media.mime_type == "image/webp":
        return "smart_remake_product_ref.webp"
    return "smart_remake_product_ref.jpg"


def _product_description(product_lock: dict[str, Any]) -> str:
    identity = product_lock.get("visualIdentity", {})
    parts = [
        f"Product type: {product_lock.get('productType', 'product')}",
        f"Colors: {'; '.join(identity.get('colors') or [])}" if identity.get("colors") else "",
        f"Shape: {identity.get('shape')}" if identity.get("shape") else "",
        f"Texture: {identity.get('texture')}" if identity.get("texture") else "",
        f"Material: {identity.get('material')}" if identity.get("material") else "",
        f"Must preserve: {'; '.join(product_lock.get('mustPreserve') or [])}" if product_lock.get("mustPreserve") else "",
    ]
    return "\n".join(part for part in parts if part)


def _audio_flags(audio_plan: dict[str, Any] | None) -> dict[str, bool]:
    if not audio_plan or audio_plan.get("mode") == "silent":
        return {"allow_music": False, "allow_voice": False}
    reference_music = audio_plan.get("referenceMusic") if isinstance(audio_plan.get("referenceMusic"), dict) else {}
    return {
        "allow_music": bool(audio_plan.get("music") and reference_music.get("mode") != "extract"),
        "allow_voice": bool(audio_plan.get("dialogue")),
    }


async def prepare_flowkit_job(
    *,
    flowkit: SmartRemakeFlowKit,
    project_name: str,
    product_lock: dict[str, Any],
    scene_map: dict[str, Any],
    audio_plan: dict[str, Any] | None,
    product_image: UploadedMedia,
) -> dict[str, Any]:
    assert_product_image(product_image)
    assert_no_reference_video_in_render_payload(scene_map)
    character_name = product_lock["productReference"]["characterName"]
    for scene in scene_map["scenes"]:
        if scene.get("chainType") != "ROOT" or scene.get("parentSceneId") is not None:
            raise SmartRemakeValidationError(
                "Smart Remake render supports ROOT scenes only.",
                "INVALID_FLOWKIT_SCENE_PAYLOAD",
            )
        if character_name not in scene.get("characterNames", []):
            raise SmartRemakeValidationError(
                "Smart Remake scene must include product character.",
                "INVALID_FLOWKIT_SCENE_PAYLOAD",
            )
        assert_no_reference_video_in_render_payload(scene)

    health = await flowkit.check_health()
    if health.get("ok") is False or health.get("status") == "offline":
        raise SmartRemakeError("FlowKit is unavailable.", "FLOWKIT_UNAVAILABLE", {"health": health})
    if health.get("extension_connected") is False:
        raise SmartRemakeError(
            "FlowKit Chrome extension is disconnected.",
            "FLOWKIT_EXTENSION_DISCONNECTED",
            {"health": health},
        )
    await flowkit.check_google_flow_auth()

    description = _product_description(product_lock)
    project = await flowkit.create_project(
        {
            "name": normalize_project_name(project_name, character_name),
            "description": description,
            "story": description,
            "material": "realistic",
            **_audio_flags(audio_plan),
            "characters": [
                {
                    "name": character_name,
                    "entity_type": "visual_asset",
                    "description": description,
                }
            ],
        }
    )
    upload = await flowkit.upload_product_image(
        bytes_data=product_image.bytes,
        mime_type=product_image.mime_type,
        project_id=project["id"],
        file_name=_image_filename(product_image),
    )
    characters = await flowkit.list_project_characters(project["id"])
    product_character = next((item for item in characters if item.get("name") == character_name), None)
    if not product_character:
        raise SmartRemakeError(
            "FlowKit project is missing the Smart Remake product character.",
            "FLOWKIT_INVALID_RESPONSE",
            {"projectId": project["id"], "productCharacterName": character_name},
        )
    await flowkit.update_project_character(project["id"], product_character["id"], {"media_id": upload["media_id"]})
    video = await flowkit.create_video(
        {
            "project_id": project["id"],
            "orientation": "VERTICAL",
            "title": normalize_project_name(project_name, character_name),
        }
    )
    prepared_scenes = []
    for scene in scene_map["scenes"]:
        created = await flowkit.create_scene(
            {
                "video_id": video["id"],
                "display_order": scene["displayOrder"],
                "chain_type": scene["chainType"],
                "parent_scene_id": scene.get("parentSceneId"),
                "character_names": scene["characterNames"],
                "prompt": scene["prompt"],
                "image_prompt": scene["imagePrompt"],
                "video_prompt": scene["videoPrompt"],
            }
        )
        prepared_scenes.append(
            {
                "smartRemakeDisplayOrder": scene["displayOrder"],
                "flowKitSceneId": created["id"],
            }
        )

    for request_type in ("GENERATE_IMAGE", "GENERATE_VIDEO"):
        assert_allowed_request_type(request_type)

    return {
        "projectId": project["id"],
        "videoId": video["id"],
        "productCharacter": {
            "id": product_character["id"],
            "name": character_name,
            "mediaId": upload["media_id"],
        },
        "scenes": prepared_scenes,
    }


def build_image_requests(prepared: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "type": "GENERATE_IMAGE",
            "scene_id": scene["flowKitSceneId"],
            "project_id": prepared["projectId"],
            "video_id": prepared["videoId"],
            "orientation": "VERTICAL",
        }
        for scene in prepared["scenes"]
    ]


def build_video_requests(prepared: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "type": "GENERATE_VIDEO",
            "scene_id": scene["flowKitSceneId"],
            "project_id": prepared["projectId"],
            "video_id": prepared["videoId"],
            "orientation": "VERTICAL",
        }
        for scene in prepared["scenes"]
    ]
