# Domain Model

- Users identify authenticated principals through provider-neutral `external_auth_id`.
- Workspaces are tenant boundaries.
- Workspace members attach users to workspaces with owner/admin/editor/viewer roles.
- Products belong to workspaces and are soft-deleted.
- Assets belong to workspaces and may link to a product.
- Asset versions are immutable upload records after completion.
- Processing jobs persist async work and output.
- Recommendations store future advice/action records without implementing scoring.

Future entities include references, boards, campaigns, angles, creators, samples, rights, and metrics.
