# Authorization

## Contents
- Find the existing model
- Rules
- Common failure patterns
- Testing authorization

## Find the existing model

Look for: role enums, permission tables, policy classes, guards/decorators/annotations with role or permission arguments, ownership checks in services or queries, multi-tenant scoping (tenant/org/workspace IDs on tables, query filters, row-level security), and external policy engines.

Typical models are RBAC (roles → permissions), ownership-based checks, ABAC/policy rules, and tenant isolation. Use whatever the project uses. Add a role or permission through the existing mechanism, and don't introduce a parallel one.

## Rules

- **Check on the server, for every request.** Hiding a button isn't authorization.
- **Check at the right layer.** Put the check where existing checks live: route guard, service method, or query scope. If the project relies on query scoping (every query filtered by tenant or owner), new queries must apply the same scope.
- **Deny by default.** A new endpoint should require the most restrictive reasonable permission until told otherwise.
- **Authorize the object, not just the route.** "Can edit orders" isn't enough. You also need "can edit *this* order", by ownership or tenant.
- **Derive the subject from the authenticated context**, never from request parameters such as a `userId` in the body.
- **Check field-level writes.** Prevent mass assignment of fields like `role`, `isAdmin`, `ownerId`, or `tenantId` by using the project's DTO/allowlist pattern.

## Common failure patterns

- IDOR: `GET /invoices/{id}` returns any invoice when the ID is known.
- Missing a check on one of several routes to the same data (list vs. detail vs. export vs. bulk).
- Checking permissions in the controller but calling the service from another path (job, consumer, GraphQL resolver) that skips the check.
- Caching responses across users or tenants.
- Admin-only endpoints protected only by obscurity.

## Testing authorization

For each protected operation, test at least: allowed role/owner → success; authenticated but unauthorized → 403 (or 404, per convention); another tenant's or user's object → denied; unauthenticated → 401. Use the project's existing helpers for creating users with roles.
