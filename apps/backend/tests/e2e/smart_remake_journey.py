"""Browser actions and read-only polling against real P0 endpoints.

APIRequestContext calls below are authenticated network requests. No browser
request is intercepted, and no lifecycle response is manufactured by this file.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
from typing import Any
from uuid import uuid4


class SmartRemakeJourney:
    def __init__(self, page: Any, stack: Any) -> None:
        self.page, self.stack = page, stack
        self.root = ""
        self.project_id = ""

    async def workspace(self) -> None:
        response = await self.page.context.request.get(
            f"{self.stack.base_url}/api/backend/workspaces"
        )
        assert response.status == 200
        workspaces = (await response.json())["data"]
        self.root = (
            f"{self.stack.base_url}/api/backend/workspaces/{workspaces[0]['id']}/smart-remake"
        )

    async def project(self) -> dict[str, Any]:
        response = await self.page.context.request.get(f"{self.root}/projects/{self.project_id}")
        assert response.status == 200, f"Project read failed ({response.status})"
        return (await response.json())["data"]

    async def create_intake(self, *, declared: bool = True, cap: str = "10.00") -> dict[str, Any]:
        declaration = {
            "basis": "owned",
            "scope": "Internal offline QA only",
            "declared": declared,
            "evidenceNote": "Self-authored lavfi and Pillow primitives",
            "revoked": False,
        }
        metadata = {
            "idempotencyKey": str(uuid4()),
            "projectName": "Offline gate case",
            "targetDuration": 8,
            "requirements": {
                "intent": "Show the orange box",
                "keep": [],
                "replace": [],
                "forbid": [],
                "claims": [],
                "requiresCharacter": False,
            },
            "rights": {
                "source": declaration,
                "product": declaration,
                "providerDisclosureAcknowledged": True,
            },
            "budget": {"capUsd": cap, "maxAttempts": 100, "maxDurationSeconds": 3600},
        }
        response = await self.page.context.request.post(
            f"{self.root}/projects",
            headers={"Origin": self.stack.base_url},
            multipart={
                "metadata": json.dumps(metadata),
                "referenceVideo": {
                    "name": "source.mp4",
                    "mimeType": "video/mp4",
                    "buffer": self.stack.media["source"].read_bytes(),
                },
                "productImage": {
                    "name": "product.png",
                    "mimeType": "image/png",
                    "buffer": self.stack.media["product"].read_bytes(),
                },
            },
        )
        assert response.status == 200
        project = (await response.json())["data"]["project"]
        self.project_id = project["id"]
        return project

    async def mutate(self, action: str, payload: dict[str, Any], *, status: int = 200) -> Any:
        project = await self.project()
        response = await self.page.context.request.post(
            f"{self.root}/projects/{self.project_id}/{action}",
            headers={"Origin": self.stack.base_url},
            data={
                "expectedRevision": project["revision"],
                "idempotencyKey": str(uuid4()),
                **payload,
            },
        )
        body = await response.json()
        assert (
            response.status == status
        ), f"{action}: HTTP {response.status}; code={body.get('error', {}).get('code')}"
        return body

    async def wait_idle(self, *, timeout: int = 180) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            project = await self.project()
            pending = project.get("pendingOperation")
            if pending and pending.get("needsReconciliation"):
                raise AssertionError(f"Worker needs reconciliation: {pending.get('errorCode')}")
            if not pending:
                last = project.get("lastOperation") or {}
                assert last.get("status") != "failed", last.get("errorCode")
                return project
            await asyncio.sleep(0.2)
        raise AssertionError(f"Worker did not complete within {timeout}s; inspect worker.log")

    async def fill_prepare(self, duration: int) -> None:
        page = self.page
        await page.get_by_label("Chọn file video mẫu", exact=True).set_input_files(
            str(self.stack.media["source"])
        )
        await page.get_by_label("Chọn ảnh sản phẩm", exact=True).set_input_files(
            str(self.stack.media["product"])
        )
        await page.get_by_role("button", name=f"{duration} giây", exact=True).click()
        await page.get_by_label("Mục tiêu video", exact=True).fill(
            "Show the self-authored orange product box with original source action."
        )
        for label in ("Tôi có quyền sử dụng video mẫu", "Tôi có quyền sử dụng ảnh sản phẩm"):
            await page.get_by_label(label, exact=True).check()
        scopes = page.get_by_label("Phạm vi được dùng", exact=True)
        notes = page.get_by_label("Ghi chú bằng chứng quyền")
        for index in range(await scopes.count()):
            await scopes.nth(index).fill("Internal offline QA and AI processing only")
            await notes.nth(index).fill(
                "Generated locally from lavfi and Pillow; no third party input"
            )
        await page.get_by_label(
            "Tôi đồng ý gửi tư liệu tới nhà cung cấp AI để xử lý và xuất video có nhãn AI.",
            exact=True,
        ).check()
        # These are synthetic limits for the local fake-provider run, not a live cap.
        await page.get_by_label("Trần chi phí (USD)", exact=True).fill("10.00")
        await page.get_by_label("Tối đa lượt trả phí", exact=True).fill("100")
        await page.get_by_label("Giới hạn thời gian (giây)", exact=True).fill("3600")

    async def analyze(self, duration: int) -> dict[str, Any]:
        page = self.page
        button = page.get_by_role("button", name="Xem gợi ý kịch bản", exact=True)
        try:
            await page.wait_for_function(
                """() => [...document.querySelectorAll('button')]
                .some(button => button.textContent.includes('Xem gợi ý kịch bản')
                    && !button.disabled)
            """,
                timeout=5000,
            )
        except Exception as exc:
            diagnostic = {
                "status": await page.get_by_role("status").all_text_contents(),
                "video": await page.locator("video").evaluate_all("""videos => videos.map(v => ({
                    duration: v.duration, ready: v.readyState, error: v.error?.message
                }))"""),
                "fields": await page.locator(
                    "input,textarea"
                ).evaluate_all("""fields => fields.map(v => ({
                    type: v.type, value: v.type === 'file' ? v.files?.length : v.value,
                    checked: v.checked
                }))"""),
            }
            (self.stack.root / "prepare-disabled-diagnostic.json").write_text(
                json.dumps(diagnostic, indent=2)
            )
            raise AssertionError(
                f"Analyze is disabled; status={diagnostic['status']}; video={diagnostic['video']}"
            ) from exc
        async with page.expect_response(
            lambda response: response.request.method == "POST"
            and response.url.endswith("/compile"),
            timeout=60000,
        ) as compiled:
            await button.click()
        response = await compiled.value
        assert response.status == 200, "Compile did not pass the owned intake gate"
        result = (await response.json())["data"]
        self.project_id = result["projectId"]
        await page.get_by_role("heading", name="Xem và chỉnh kịch bản", exact=True).wait_for()
        cuts = [2] if duration == 8 else [3, 8, 12]
        for index, second in enumerate(cuts):
            await page.get_by_label(f"Mốc cắt sau cảnh {index + 1}, giây", exact=True).fill(
                str(second)
            )
        async with page.expect_response(
            lambda response: response.request.method == "POST"
            and response.url.endswith("/compile"),
            timeout=60000,
        ) as recompiled:
            await page.get_by_role("button", name="Cập nhật kịch bản", exact=True).click()
        response = await recompiled.value
        assert response.status == 200
        result = (await response.json())["data"]
        assert result["projectId"] == self.project_id, "Compile must preserve the intake project"
        return result

    async def refresh_ui(self) -> None:
        await self.page.get_by_role("button", name="Làm mới dự án", exact=True).click()

    async def choose_ranges(self, starts: list[int], *, indexes: list[int] | None = None) -> None:
        for index in indexes if indexes is not None else range(len(starts)):
            await (
                self.page.get_by_role("region", name="Kết quả Smart Remake", exact=True)
                .get_by_role("button")
                .filter(has=self.page.get_by_text(f"Cảnh {index + 1}", exact=True))
                .click()
            )
            await self.page.get_by_label("Bắt đầu (giây)", exact=True).fill(str(starts[index]))
            async with self.page.expect_response(
                lambda response: response.request.method == "PATCH"
                and response.url.endswith("/timeline"),
                timeout=30000,
            ) as saved:
                await self.page.get_by_role("button", name="Dùng đoạn này", exact=True).click()
            assert (await saved.value).status == 200

    async def compose(self, duration: int) -> dict[str, Any]:
        async with self.page.expect_response(
            lambda response: response.request.method == "POST"
            and response.url.endswith("/publish"),
            timeout=30000,
        ) as submitted:
            await self.page.get_by_role(
                "button", name=f"Ghép video · {duration} giây", exact=True
            ).click()
        assert (await submitted.value).status == 200
        project = await self.wait_idle()
        assert project["assemblies"]["activeAssemblyId"]
        await self.refresh_ui()
        return project

    async def inspect_assembly(self) -> dict[str, Any]:
        before = await self.project()
        assembly_id = before["assemblies"]["activeAssemblyId"]
        await self.page.get_by_label("Kiểm tra tư liệu").select_option(label="Video MP4 đã ghép")
        async with self.page.expect_response(
            lambda response: response.request.method == "POST"
            and response.url.endswith("/inspections"),
            timeout=30000,
        ) as submitted:
            await self.page.get_by_role("button", name="Kiểm tra bằng AI", exact=True).click()
        assert (await submitted.value).status == 200
        project = await self.wait_idle()
        report = next(
            item
            for item in reversed(project["inspectionSummary"]["reports"])
            if item["subject"].get("assemblyId") == assembly_id
        )
        assert report["findings"] and report["observations"]
        await self.refresh_ui()
        return report

    async def review_semantics(self, report: dict[str, Any]) -> None:
        article = self.page.get_by_role("article").filter(
            has=self.page.locator(f'time[datetime="{report["checkedAt"]}"]')
        )
        for finding in report["findings"]:
            if finding["status"] == "passed":
                continue
            assert not finding.get(
                "hardBlocking"
            ), "Fixture unexpectedly has a hard technical failure"
            assert finding["status"] == "needs_review", "Missing evidence cannot be approved"
            card = article.get_by_role(
                "heading", name=re.compile(rf"^{re.escape(finding['requirementId'])} · ")
            ).locator("..")
            await card.get_by_label("Lý do nhận xét", exact=True).fill(
                "Reviewed local fixture video and original owned references."
            )
            async with self.page.expect_response(
                lambda response: response.request.method == "POST"
                and response.url.endswith("/inspection-reviews")
            ) as reviewed:
                await card.get_by_role("button", name="Chấp nhận finding", exact=True).click()
            assert (await reviewed.value).status == 200
            assert any(
                review["reportId"] == report["id"]
                and review["findingId"] == finding["id"]
                and review["decision"] == "accept"
                for review in (await self.project())["inspectionSummary"]["reviews"]
            )

    async def inspect_scene(self) -> dict[str, Any]:
        project = await self.project()
        scene = project["scenes"][0]
        version_id = scene["activeVersionId"]
        await self.page.get_by_label("Kiểm tra tư liệu").select_option(
            value=json.dumps(
                {"kind": "scene", "sceneId": scene["id"], "versionId": version_id},
                separators=(",", ":"),
            )
        )
        async with self.page.expect_response(
            lambda response: response.request.method == "POST"
            and response.url.endswith("/inspections")
        ) as submitted:
            await self.page.get_by_role("button", name="Kiểm tra bằng AI", exact=True).click()
        assert (await submitted.value).status == 200
        project = await self.wait_idle()
        report = next(
            report
            for report in reversed(project["inspectionSummary"]["reports"])
            if report["subject"].get("sceneId") == scene["id"]
            and report["subject"].get("versionId") == version_id
        )
        await self.refresh_ui()
        return report

    def scene_hashes(self, project: dict[str, Any]) -> dict[str, str]:
        return {
            scene["id"]: next(
                version["mediaHash"]
                for version in scene["versions"]
                if version["id"] == scene["activeVersionId"]
            )
            for scene in project["scenes"]
        }

    async def assert_reload_is_read_only(self) -> None:
        before = self.stack.calls()
        writes = []

        def watch(request: Any) -> None:
            if "/smart-remake/" in request.url and request.method != "GET":
                writes.append(request.method)

        self.page.on("request", watch)
        try:
            await self.page.reload()
            await self.page.get_by_role(
                "region", name="Kết quả Smart Remake", exact=True
            ).wait_for()
            await self.page.wait_for_load_state("networkidle")
            assert not writes, "Reload must only read/poll existing work"
            assert self.stack.calls() == before, "Reload must not create new paid attempts"
        finally:
            self.page.remove_listener("request", watch)

    async def fetch_export(self, exported: dict[str, Any]) -> bytes:
        response = await self.page.context.request.get(exported["downloadUrl"])
        assert response.status == 200
        data = await response.body()
        assert hashlib.sha256(data).hexdigest() == exported["exportMediaHash"]
        assert data, "Checked export must contain actual MP4 bytes"
        return data
