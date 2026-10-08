# Authentication

## Contents
- First, find what already exists
- Decision guide
- Principles regardless of library
- Sessions and tokens
- Credentials and secrets
- Boundaries
- Testing authentication

## First, find what already exists

Authentication is the area where agents most often add a redundant library. Before writing code, search for:

- Auth dependencies: auth frameworks, OAuth/OIDC clients, JWT libraries, session middleware, password-hashing libraries.
- Middleware, guards, filters, or decorators that set a "current user".
- Login/logout/callback routes, user/account/session tables or models, identity-provider configuration (issuer URLs, client IDs in `.env.example`).
- Infrastructure that does auth in front of the app: API gateway, reverse proxy, service mesh, platform auth headers.

Then classify what you found:

| Found | Action |
|-------|--------|
| A working auth system | Extend it: protect new routes with the existing guard, add a provider through its plugin mechanism. Don't replace it. |
| Partial auth (e.g. user table and password hashing, but no session handling) | Complete it with the framework's built-in or already-installed mechanism. |
| No auth at all | Propose an approach that fits the framework and deployment, and confirm before adding a dependency (see below). |
| Auth handled upstream (gateway/proxy) | Consume the verified identity the way existing code does. Don't add a second login. |

"Add authentication" in a repository that already has it usually means "protect these routes" or "add this login method". Confirm the intended scope from the code and the request.

## Decision guide

When nothing exists and a choice is needed:

1. Prefer the framework's first-party or conventional mechanism, such as the framework's security module, built-in auth app, or authentication middleware.
2. Prefer delegating to an existing identity provider (OIDC/SAML) if the organization or deployment already uses one.
3. Otherwise choose a well-maintained library that's commonly used with this exact framework and version. Explain the choice and its alternatives briefly, and get confirmation before installing.
4. Never write your own cryptography, token formats, or password hashing primitives.

## Principles regardless of library

- **Identity** (who), **authentication** (prove it), and **authorization** (what they may do) are separate concerns. See [authorization.md](authorization.md).
- Authenticate on the server. Client-side checks are only for UX.
- Use generic login failure messages to prevent account enumeration, and apply rate limiting or lockout on login, reset, and verification endpoints.
- Re-authenticate for sensitive actions (changing email/password, MFA settings) if the product requires it.
- Log authentication events (success, failure, lockout) without logging secrets, tokens, or passwords.

## Sessions and tokens

- **Server-side sessions**: cookie with `HttpOnly`, `Secure`, an appropriate `SameSite`, a scoped path/domain, rotated on login and privilege change, invalidated on logout.
- **Bearer tokens (e.g. JWT)**: verify the signature with the expected algorithm (reject `none` and algorithm confusion), and verify `exp`, `nbf`, `iss`, and `aud`. Keep access tokens short-lived. Don't put sensitive data in token payloads.
- **Refresh**: refresh tokens are long-lived secrets. Store them securely, rotate them on use, detect reuse if the project supports it, and support revocation.
- **Browser storage**: prefer HttpOnly cookies for browser apps. Tokens in `localStorage` are exposed to XSS. If cookies carry auth, CSRF protection is needed (see [security.md](security.md)).
- **Service-to-service**: use the existing mechanism (mTLS, signed tokens, workload identity). Don't add shared static secrets in code.

## Credentials and secrets

- Hash passwords with a slow, salted algorithm (Argon2id, scrypt, bcrypt, or PBKDF2 with a high work factor), preferably through the framework or the library already used. Never store plaintext or reversibly encrypted passwords.
- Secrets come from environment/config/secret managers the way the project already loads them. Never hard-code them, commit them, or log them. Add new variables to `.env.example` or the config docs, with placeholder values only.
- Password reset and verification tokens should be random, single-use, short-lived, and stored hashed.

## Boundaries

- Know where authentication is enforced: global middleware with public exceptions, or per-route opt-in. New routes must end up on the correct side. Default-deny is safer when the project supports it.
- In frameworks that mix server and client code, enforce auth on the server (route handlers, server actions, middleware, API layer), not only in UI components.
- Background jobs and message consumers have no user session. Pass identity explicitly and re-check authorization if needed.

## Testing authentication

Use the project's existing auth test helpers (test users, token factories, mock security contexts). Cover:
- Unauthenticated request → rejected (401 or a redirect, matching the convention).
- Authenticated request → allowed.
- Expired or invalid token/session → rejected.
- Logout or revocation → the old session/token no longer works.
- Login failure paths: wrong password, unknown user (same response), rate limiting if implemented.
