# Auth Contract

Clients send `Authorization: Bearer <access-token>`. The backend selects the verifier from `AUTH_MODE`: native `password`, external `oidc`, or local-only `local_test`.

## Native email/password

| Endpoint                     | Request                                                  | Result                                                                              |
| ---------------------------- | -------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| `POST /api/v1/auth/register` | `email`, `display_name`, `password` (12–1024 characters) | Creates an account and private owner workspace; returns tokens in the API envelope. |
| `POST /api/v1/auth/login`    | `email`, `password`                                      | Returns an access JWT and refresh token.                                            |
| `POST /api/v1/auth/refresh`  | `refresh_token`                                          | Rotates the refresh token and issues a new access JWT.                              |
| `POST /api/v1/auth/logout`   | `refresh_token`                                          | Revokes the associated session; returns 204.                                        |
| `GET /api/v1/me`             | Bearer access JWT                                        | Returns the active user's profile, including nullable `phone_number`.               |

Token responses contain `access_token`, `refresh_token`, `token_type` (`Bearer`) and `expires_in`. Access JWTs use HS256 with a server-only secret and validate issuer, audience, subject, session, issuance and expiration. Every protected request also checks that the database session and user remain active. Logout and detected refresh-token replay revoke that session, including outstanding access JWTs. A duplicate refresh in the first five seconds returns 409 without revoking the session, allowing overlapping requests to finish.

The browser submits credentials to same-origin frontend endpoints `/api/auth/register` and `/api/auth/login`. The frontend server stores tokens in HttpOnly cookies and returns only authentication state and a sanitized internal destination to JavaScript. The browser uses `/api/backend/*` for authenticated API calls; it does not store JWTs in localStorage. Mutating frontend endpoints enforce same-origin requests. Production cookies use Secure and the `__Host-` prefix.

Email addresses are case-normalized and unique among password accounts. Passwords are hashed with Argon2id. Refresh tokens are random and only their SHA-256 hashes are persisted. Redis rate limits are shared across backend instances and fail closed on Redis outages. This flow does not yet provide email verification or password-reset email; it must not present native accounts as email-verified.

See the local development runbook for signing secrets, migration and deployment configuration. Local development may explicitly use `Bearer local-test`; staging and production reject that mode.
