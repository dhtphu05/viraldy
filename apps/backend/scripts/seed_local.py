from __future__ import annotations

from sqlalchemy import select

from viraldy.modules.assets.models import AssetModel, AssetVersionModel
from viraldy.modules.identity.models import UserModel
from viraldy.modules.products.contracts import (
    BuyerPersonaV1,
    ClaimRuleV1,
    CreativeContextV1,
    ProductBenefitV1,
    ProductContextV1,
    ProductFeatureV1,
    ProductGovernanceV1,
    ProductIdentityV1,
    build_minimal_product_context,
    product_context_to_json,
)
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
            product_context = build_minimal_product_context(
                name="CounterSpace Rack",
                description="TikTok Shop demo product for small-kitchen organization.",
                market="US",
                metadata_json={
                    "fixture_id": "viraldy-demo-product-v1",
                    "category": "home_organization",
                },
            )
            product = ProductModel(
                workspace_id=workspace.id,
                name="CounterSpace Rack",
                description="TikTok Shop demo product for small-kitchen organization.",
                status="active",
                market="US",
                created_by_user_id=user.id,
                metadata_json={
                    "fixture_id": "viraldy-demo-product-v1",
                    "category": "home_organization",
                },
                product_context_json=product_context_to_json(product_context),
                context_schema_version=product_context.schema_version,
            )
            session.add(product)
            session.flush()
        else:
            product.metadata_json = {
                **product.metadata_json,
                "category": "home_organization",
            }
            product_context = build_minimal_product_context(
                name=product.name,
                description=product.description,
                market=product.market,
                metadata_json={
                    **product.metadata_json,
                    "category": "home_organization",
                },
            )
            product.product_context_json = product_context_to_json(product_context)
            product.context_schema_version = product_context.schema_version

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
        _ensure_category_fixture_pack(session, workspace.id, board.id, user.id)

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


def _ensure_category_fixture_pack(session, workspace_id, board_id, user_id) -> None:
    fixtures = [
        (
            "GlowPass Beauty Tool",
            "beauty_tool",
            "US",
            "busy beauty shopper",
            "uneven styling finish",
            "smoother-looking finish",
            "beauty tool moving through one visible section",
            "finished section shown on camera",
            "viraldy-fixture-beauty-tool-v1",
            "Beauty Tool Fixture Video",
        ),
        (
            "NameNest Custom Gift",
            "pod_personalized_gift",
            "US",
            "last-minute gift buyer",
            "generic gifts feel impersonal",
            "personalized detail feels intentional",
            "custom print detail and packaging reveal",
            "customized name detail readable on the item",
            "viraldy-fixture-pod-gift-v1",
            "POD Gift Fixture Video",
        ),
        (
            "PawReady Walk Clip",
            "pet_accessory",
            "US",
            "pet owner",
            "messy pet-walk setup",
            "walk setup is easier to handle",
            "pet accessory attached and used during setup",
            "accessory remains visible while being used",
            "viraldy-fixture-pet-accessory-v1",
            "Pet Accessory Fixture Video",
        ),
        (
            "StyleLoop Belt Bag",
            "fashion_accessory",
            "US",
            "style reviewer",
            "hard to style one accessory with different outfits",
            "accessory works with multiple outfit contexts",
            "accessory worn with two outfit contexts",
            "two outfit looks shown with accessory visible",
            "viraldy-fixture-fashion-accessory-v1",
            "Fashion Accessory Fixture Video",
        ),
    ]
    for (
        name,
        category,
        market,
        persona,
        pain,
        outcome,
        demo_mechanism,
        proof,
        fixture_id,
        title,
    ) in fixtures:
        context = _fixture_product_context(
            name=name,
            category=category,
            market=market,
            persona=persona,
            pain=pain,
            outcome=outcome,
            demo_mechanism=demo_mechanism,
            proof=proof,
        )
        product = _ensure_product(
            session,
            workspace_id,
            user_id,
            name,
            f"Seeded {category} product for creative-domain fixture evaluation.",
            market,
            {"fixture_category": category},
            context,
        )
        asset = _ensure_fixture_asset(session, workspace_id, product.id, user_id, title, fixture_id)
        _ensure_reference(
            session,
            workspace_id,
            board_id,
            product.id,
            asset.id,
            user_id,
            title,
            fixture_id,
        )


def _ensure_product(
    session,
    workspace_id,
    user_id,
    name: str,
    description: str,
    market: str,
    metadata_json: dict[str, object],
    product_context: ProductContextV1,
) -> ProductModel:
    product = session.execute(
        select(ProductModel).where(
            ProductModel.workspace_id == workspace_id,
            ProductModel.name == name,
        )
    ).scalar_one_or_none()
    if product is None:
        product = ProductModel(
            workspace_id=workspace_id,
            name=name,
            description=description,
            status="active",
            market=market,
            created_by_user_id=user_id,
            metadata_json=metadata_json,
            product_context_json=product_context_to_json(product_context),
            context_schema_version=product_context.schema_version,
        )
        session.add(product)
        session.flush()
        return product
    product.product_context_json = product_context_to_json(product_context)
    product.context_schema_version = product_context.schema_version
    return product


def _fixture_product_context(
    *,
    name: str,
    category: str,
    market: str,
    persona: str,
    pain: str,
    outcome: str,
    demo_mechanism: str,
    proof: str,
) -> ProductContextV1:
    return ProductContextV1(
        identity=ProductIdentityV1(name=name, category=category, market=market, currency="USD"),
        personas=[
            BuyerPersonaV1(
                id=f"{category}_persona_1",
                label=persona,
                pain_points=[pain],
                desired_outcomes=[outcome],
                objections=["needs observable proof before buying"],
                awareness_stage="problem_aware",
            )
        ],
        benefits=[
            ProductBenefitV1(
                id=f"{category}_benefit_1",
                label=outcome,
                description=outcome,
                proof_available=[proof],
                claim_strength="observed",
            )
        ],
        features=[
            ProductFeatureV1(
                id=f"{category}_feature_1",
                label=demo_mechanism,
                visual_demo_possible=True,
                visual_cues=[demo_mechanism],
            )
        ],
        creative=CreativeContextV1(
            primary_angles=[outcome],
            demonstration_mechanisms=[demo_mechanism],
            available_proof=[proof],
            creator_personas=[persona],
            preferred_delivery_styles=["authentic_review", "demonstration"],
            brand_voice=["clear", "evidence-led"],
        ),
        governance=ProductGovernanceV1(
            claims=[
                ClaimRuleV1(
                    id=f"{category}_claim_rule_1",
                    text="Avoid guaranteed, medical, financial, or viral-performance claims.",
                    rule_type="prohibited",
                    severity="high",
                )
            ],
            required_disclosures=["Results vary by use case."],
            prohibited_content=["unsupported before/after exaggeration"],
            rights_notes=["Rights authorization is not granted by this system."],
        ),
    )


def _ensure_reference(
    session,
    workspace_id,
    board_id,
    product_id,
    asset_id,
    user_id,
    title: str,
    fixture_id: str,
) -> None:
    reference = session.execute(
        select(ReferenceModel).where(
            ReferenceModel.workspace_id == workspace_id,
            ReferenceModel.asset_id == asset_id,
        )
    ).scalar_one_or_none()
    if reference is not None:
        return
    session.add(
        ReferenceModel(
            workspace_id=workspace_id,
            board_id=board_id,
            product_id=product_id,
            asset_id=asset_id,
            source_platform="Fixture",
            source_url=f"https://example.com/viraldy-fixtures/{fixture_id}",
            title=title,
            notes="Seeded multi-category fixture for creative-domain evaluation.",
            created_by_user_id=user_id,
        )
    )


if __name__ == "__main__":
    main()
