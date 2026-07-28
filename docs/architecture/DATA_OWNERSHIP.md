# Data Ownership

- Identity owns `users`.
- Workspaces owns `workspaces` and `workspace_members`.
- Products owns `products`.
- Assets owns `assets` and `asset_versions`.
- Jobs owns `processing_jobs`.
- Recommendations owns `recommendations` and `recommendation_actions`.

Other modules access owned data through public application contracts or stable IDs.
