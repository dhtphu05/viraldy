from __future__ import annotations

from sqlalchemy import select

from viraldy.modules.identity.infrastructure.models import UserModel
from viraldy.modules.products.infrastructure.models import ProductModel
from viraldy.modules.workspaces.infrastructure.models import WorkspaceMemberModel, WorkspaceModel
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
                ProductModel.name == "Sample Product",
            )
        ).scalar_one_or_none()
        if product is None:
            session.add(
                ProductModel(
                    workspace_id=workspace.id,
                    name="Sample Product",
                    description="Local seed product",
                    status="active",
                    created_by_user_id=user.id,
                    metadata_json={},
                )
            )
        session.commit()
        print({"user_id": str(user.id), "workspace_id": str(workspace.id)})


if __name__ == "__main__":
    main()
