# Smart Remake private R2 media

Configure these variables on the API **and worker**, without a `VITE_` prefix:

```dotenv
# Existing ACCOUNT_ID remains supported; R2_ACCOUNT_ID takes precedence.
R2_ACCOUNT_ID=<Cloudflare account ID>
R2_ACCESS_KEY_ID=<R2 S3 access key>
R2_SECRET_ACCESS_KEY=<R2 S3 secret>
R2_BUCKET=<private bucket name>
S3_PRESIGNED_EXPIRY_SECONDS=900
```

`R2_PUBLIC_BASE_URL` is not required for this private upload/export flow. Keep the
bucket private. Signed PUT/GET requests use the R2 S3 endpoint, not a custom public
domain. The adapter uses AWS Signature V4 and region `auto`.

## Browser CORS

Add the rule in `infrastructure/r2/smart-remake-cors.json` to the bucket's existing
CORS policy. The template includes `https://viraldy.vercel.app` and the local Vite
origins. Add any other exact frontend origin before deploying there. Preserve
other applications' existing rules; do not replace them blindly. Backend CORS and
R2 bucket CORS are separate settings.

The file uses the AWS S3 API wrapper (`CORSRules`); the Cloudflare dashboard expects
the array inside `CORSRules`. A credential with bucket CORS administration access
is needed to change the policy. An object read/write token can upload successfully
while CORS administration still returns `AccessDenied`.

Validate an OPTIONS request from the frontend origin with requested method PUT and
header `content-type`. The response must allow that origin and method. An expired
signed URL can look like a CORS/network failure because R2 omits CORS headers on
expired signatures.

## Request flow

1. The authenticated frontend POSTs filename, MIME, byte size and role to
   `/api/v1/workspaces/{workspaceId}/smart-remake/upload-sessions`.
2. The server validates permission, media limits and R2 configuration, creates an
   owned asset version and returns a short-lived signed PUT URL and required headers.
   Its signature binds both MIME type and exact declared byte length. Send the File
   body directly; the browser sets Content-Length automatically.
3. The browser PUTs the file directly to R2, without application cookies or a backend
   multipart proxy, then POSTs `/upload-sessions/{assetId}/complete`.
4. The frontend POSTs metadata and the completed asset-version IDs to
   `/smart-remake/projects/from-assets`. The server rechecks workspace ownership,
   size, type and actual bytes, then makes an independent canonical project copy.
   Reusing the original PUT URL cannot overwrite that project copy.
5. Approval/export still checks the current assembly, inspection, rights and media
   hash. The export endpoint generates a fresh signed GET with attachment disposition
   on each successful request, including idempotent retries. The browser opens it
   directly. Playback URLs omit attachment disposition and support byte ranges.

New R2 object keys contain `/__r2__/` **inside** their existing workspace/project
prefix. The marker selects the private R2 bucket; unmarked persisted keys continue
using the original S3/MinIO configuration. Workspace/project ownership checks remain
valid, and inventories include R2 objects for cleanup. No existing keys are renamed.
Keep the original `S3_*` configuration while existing projects still reference it.

An R2-only request fails with `SMART_REMAKE_R2_NOT_CONFIGURED` when configuration is
incomplete. It does not fall back to a local upload. Signed URLs and credentials
must not be logged or persisted in browser storage.

## Original upload cleanup

Canonical intake records the exact identities of dedicated Smart Remake uploads
in its private context. Project deletion includes these original objects as well
as canonical media, while preserving shared references and unrelated library files.
An original PUT URL can be reused until expiry, so deletion remains partial until
that upload window closes. Retrying the same deletion request finishes pending
objects after expiry. Missing or invalid expiry stays partial for review.

Generic asset metadata rows remain after object deletion to avoid deleting later
asset revisions. These rows do not retain the removed media bytes.

## Generated images and KIE prompts

Generated opening and ending images remain available in generation progress and
the completed clip's **Ảnh & prompt** dialog. Each download requests a fresh signed
attachment URL through `/projects/{projectId}/generation/{operationId}/images/{requestHash}/download`.
The API checks workspace read access and the retained image's exact project,
operation, expectations and storage binding before signing; it does not proxy bytes.

Update both the API and worker when deploying this change. New KIE submissions
save their final prompt and URL-free request fields before dispatch. The UI shows
the saved prompt only when its fingerprint matches verified submission evidence.
Historical tasks without this snapshot explicitly report that the prompt was not
saved. After Scene Fix, the dialog identifies these as original-generation assets,
not the repaired version's inputs.

References: [R2 presigned URLs](https://developers.cloudflare.com/r2/api/s3/presigned-urls/),
[R2 CORS](https://developers.cloudflare.com/r2/buckets/cors/),
[S3 API compatibility](https://developers.cloudflare.com/r2/api/s3/api/).
