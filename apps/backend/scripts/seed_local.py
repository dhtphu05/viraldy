from __future__ import annotations

from sqlalchemy import select

from viraldy.modules.assets.models import AssetModel, AssetVersionModel
from viraldy.modules.identity.models import UserModel
from viraldy.modules.products.models import ProductModel
from viraldy.modules.reference_boards.models import ReferenceBoardModel
from viraldy.modules.references.models import ReferenceModel
from viraldy.modules.workspaces.models import WorkspaceMemberModel, WorkspaceModel
from viraldy.platform.database.session import SyncSessionFactory


def main() -> None:
    with SyncSessionFactory() as session:
        user = session.execute(
            select(UserModel).where(UserModel.external_auth_id == "local-test-user")
        ).scalar_one_or_none()
        if user is None:
            user = UserModel(
                external_auth_id="local-test-user",
                email="local@viraldy.test",
                display_name="Local Viraldy User",
                status="active",
            )
            session.add(user)
            session.flush()

        workspace = session.execute(
            select(WorkspaceModel).where(WorkspaceModel.slug == "local-viraldy")
        ).scalar_one_or_none()
        if workspace is None:
            workspace = WorkspaceModel(
                name="Local Viraldy",
                slug="local-viraldy",
                status="active",
                created_by_user_id=user.id,
            )
            session.add(workspace)
            session.flush()
            session.add(
                WorkspaceMemberModel(workspace_id=workspace.id, user_id=user.id, role="owner")
            )

        product = session.execute(
            select(ProductModel).where(
                ProductModel.workspace_id == workspace.id,
                ProductModel.name == "CounterSpace Rack",
            )
        ).scalar_one_or_none()
        if product is None:
            product = ProductModel(
                workspace_id=workspace.id,
                name="CounterSpace Rack",
                description="TikTok Shop demo product for small-kitchen organization.",
                status="active",
                market="US",
                created_by_user_id=user.id,
                metadata_json={"fixture_id": "viraldy-demo-product-v1"},
            )
            session.add(product)
            session.flush()

        board = session.execute(
            select(ReferenceBoardModel).where(
                ReferenceBoardModel.workspace_id == workspace.id,
                ReferenceBoardModel.name == "Demo Creative Research",
            )
        ).scalar_one_or_none()
        if board is None:
            board = ReferenceBoardModel(
                workspace_id=workspace.id,
                product_id=product.id,
                name="Demo Creative Research",
                description="Seeded board for local fixture-mode MVP smoke tests.",
                board_type="creative_research",
                created_by_user_id=user.id,
            )
            session.add(board)
            session.flush()

        reference_asset = _ensure_fixture_asset(
            session,
            workspace.id,
            product.id,
            user.id,
            "Demo Reference Video",
            "viraldy-demo-reference-v1",
        )
        _ensure_fixture_asset(
            session,
            workspace.id,
            product.id,
            user.id,
            "Demo Quick Score Video",
            "viraldy-demo-quick-v1",
        )
        _ensure_fixture_asset(
            session,
            workspace.id,
            product.id,
            user.id,
            "Demo UGC Draft Fixable",
            "viraldy-demo-ugc-fixable-v1",
        )

        reference = session.execute(
            select(ReferenceModel).where(
                ReferenceModel.workspace_id == workspace.id,
                ReferenceModel.asset_id == reference_asset.id,
            )
        ).scalar_one_or_none()
        if reference is None:
            session.add(
                ReferenceModel(
                    workspace_id=workspace.id,
                    board_id=board.id,
                    product_id=product.id,
                    asset_id=reference_asset.id,
                    source_platform="TikTok",
                    source_url="https://www.tiktok.com/@viraldy/demo-reference",
                    title="Counter reset reference",
                    notes="Known fixture for Creative DNA analysis.",
                    created_by_user_id=user.id,
                )
            )
        session.commit()
        print(
            {
                "user_id": str(user.id),
                "workspace_id": str(workspace.id),
                "product_id": str(product.id),
                "board_id": str(board.id),
            }
        )


def _ensure_fixture_asset(
    session,
    workspace_id,
    product_id,
    user_id,
    title: str,
    fixture_id: str,
) -> AssetModel:
    asset = session.execute(
        select(AssetModel).where(
            AssetModel.workspace_id == workspace_id,
            AssetModel.metadata_json["fixture_id"].astext == fixture_id,
        )
    ).scalar_one_or_none()
    if asset is not None:
        return asset

    asset = AssetModel(
        workspace_id=workspace_id,
        product_id=product_id,
        asset_type="video",
        status="uploaded",
        created_by_user_id=user_id,
        metadata_json={"fixture_id": fixture_id, "title": title},
    )
    session.add(asset)
    session.flush()
    version = AssetVersionModel(
        asset_id=asset.id,
        version_number=1,
        storage_key=f"fixtures/{fixture_id}.mp4",
        original_filename=f"{fixture_id}.mp4",
        declared_mime_type="video/mp4",
        detected_mime_type="video/mp4",
        size_bytes=1024,
        checksum_sha256=fixture_id,
        duration_ms=28000,
        width=1080,
        height=1920,
        metadata_json={"fixture_id": fixture_id},
        validation_status="uploaded",
    )
    session.add(version)
    session.flush()
    asset.current_version_id = version.id
    return asset


if __name__ == "__main__":
    main()
