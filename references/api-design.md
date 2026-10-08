# API design

## Contents
- Identify the paradigm first
- HTTP semantics
- Request validation
- Response and error consistency
- Pagination, filtering, sorting
- Idempotency and retries
- Compatibility and versioning
- Non-REST paradigms

## Identify the paradigm first

Check what the project exposes before designing anything: REST/JSON over HTTP, GraphQL (schema files, resolvers), gRPC (`*.proto`), tRPC, JSON-RPC, server actions, WebSockets, or message-based APIs (topics, queues). Extend the existing paradigm. Don't add REST endpoints to a GraphQL API, or the reverse, unless asked.

If the project has an API contract (an OpenAPI spec, a GraphQL schema, proto files), find out whether it's **contract-first** (the spec generates code) or **code-first** (the code generates the spec). Then update the source of truth and regenerate.

## HTTP semantics

Follow the project's existing usage, and stay within standard HTTP semantics:

- `GET` is safe and has no side effects. `PUT` replaces and is idempotent. `PATCH` partially updates. `DELETE` is idempotent. `POST` creates or triggers an action.
- Status codes: `201` (with a `Location` header or the created resource, following project convention) for creation, `204` for empty success, `400`/`422` for validation errors (whichever the project uses), `401` unauthenticated, `403` forbidden, `404` not found, `409` conflict (duplicate, version mismatch), `429` rate-limited.
- Decide deliberately whether a forbidden resource should return 404 instead of 403, to avoid revealing that it exists. Match existing behavior.

## Request validation

- Validate at the boundary, using the project's mechanism (see the inventory in [conventions.md](conventions.md)).
- Validate type, presence, length/range, format, and enum membership. Reject unknown fields if the project does.
- Normalize where the project normalizes, for example trimming strings or lower-casing emails.
- Don't trust client-supplied identifiers for ownership. Derive the acting user from the auth context.
- Cap list sizes, page sizes, string lengths, and upload sizes.

## Response and error consistency

- Use the existing response envelope, field casing, date/time format, and null-vs-omitted convention.
- Map errors through the existing global error handler. Don't build ad-hoc error bodies in individual handlers.
- Error bodies shouldn't leak stack traces, SQL, internal hostnames, or other users' data.
- Never return persistence entities directly if the project uses DTOs or response models. That can expose internal fields such as password hashes or internal flags.

## Pagination, filtering, sorting

- Reuse the existing pagination shape (offset/limit, page/size, cursor/next token) and parameter names.
- If there's none yet: cursor/keyset pagination for large or frequently changing collections, offset for small admin lists. Always set a default and a maximum page size.
- Pagination needs a **deterministic order**. Sort by a unique key, or add a tiebreaker such as the primary key.
- Whitelist filterable and sortable fields. Never interpolate client-supplied field names or directions into SQL.
- Decide whether a total count is required. `COUNT(*)` on large tables can be expensive.
- Back the filter and sort columns with appropriate indexes (see [database.md](database.md)).

## Idempotency and retries

- Operations that clients or queues may retry (payments, order creation, webhooks, message consumers) need an idempotency strategy: an idempotency key, a natural unique constraint, or upsert semantics. Use the mechanism the project already has.
- External calls need timeouts. Retries need backoff and should only be applied to idempotent operations.

## Compatibility and versioning

- Adding optional fields and new endpoints is usually safe. Removing or renaming fields, changing types, making optional inputs required, or changing error codes is breaking.
- Follow the existing versioning scheme (URL prefix, header, media type, or none). Don't introduce versioning for one change.
- If a breaking change is unavoidable: say so explicitly, and propose a deprecation path such as supporting both shapes for a while.
- Update the API docs and spec the project maintains, plus client SDKs or generated types in the same repo.

## Non-REST paradigms

- **GraphQL**: watch for N+1 queries in resolvers (use the project's batching/DataLoader pattern), enforce authorization per field or per resolver as the project does, respect query depth and complexity limits, and treat nullability changes as breaking.
- **gRPC/protobuf**: never reuse or renumber field tags. Add new fields as optional. Reserve removed tags and names. Run the project's breaking-change check if it has one.
- **Events/messages**: version schemas, keep consumers tolerant of unknown fields, make handlers idempotent, and define behavior for poison messages.
