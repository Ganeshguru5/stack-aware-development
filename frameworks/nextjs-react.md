# Next.js / React

## Contents
- Inspect the application
- Router model and boundaries
- Data fetching and mutations
- Common patterns to reuse
- Pitfalls
- Security
- Performance
- Testing

## Inspect the application

- `next` version from the lockfile. Conventions differ between major versions, so check the installed version's docs or the project's own code before using an API.
- **Router**: `app/` (App Router), `pages/` (Pages Router), or both during a migration (possibly under `src/`). New routes go in the router the surrounding feature uses.
- `next.config.*`: output mode (standalone, static export), images, rewrites/redirects, experimental flags.
- `middleware.ts` (or its successor in newer versions, if present): auth gating, redirects, and which paths its `matcher` covers.
- Data layer: ORM/client location (often `lib/db`, `server/`, `prisma/`), API routes (`app/api/**/route.ts` or `pages/api/**`), server actions (`"use server"`), tRPC/GraphQL clients.
- Auth: existing auth library config, session helpers, middleware checks. See [authentication](../references/authentication.md).
- UI: component library, styling (Tailwind, CSS Modules, CSS-in-JS), form library, client data library (React Query/SWR), global state.
- For a React SPA without Next.js: bundler (Vite etc.), router library and version, data fetching approach.

## Router model and boundaries

- **App Router**: components are Server Components by default. `"use client"` marks a client boundary, and everything imported into it becomes client code. Keep DB access, secrets, and server SDKs in server-only modules (use the `server-only` package if the project does).
- Pass only serializable props from server to client components.
- **Pages Router**: data loading via `getServerSideProps`/`getStaticProps`/API routes. Don't introduce App Router APIs into Pages Router files.
- Route handlers, server actions, and middleware all run on the server, but can have different runtimes (Node vs edge). Edge runtimes lack many Node APIs and some DB drivers. Check the runtime config.

## Data fetching and mutations

- Follow the existing approach: server component fetching, server actions with revalidation, API routes plus client fetching, or React Query/SWR hooks.
- Caching and revalidation semantics vary across Next.js versions. Copy the neighbor's pattern (`fetch` cache options, `revalidatePath`/`revalidateTag`, route segment config) and check the installed version's behavior.
- Validate server action and route handler input on the server with the project's schema library. Server actions are public endpoints.

## Common patterns to reuse

Existing `lib/` helpers (db client singleton, auth/session getters, fetch wrappers), the UI component library, form and validation schemas shared between client and server, error and loading conventions (`error.tsx`, `loading.tsx`, `not-found.tsx` or their Pages Router equivalents), layouts.

## Pitfalls

- Instantiating the DB client per request or per hot reload. Reuse the project's singleton pattern.
- Importing server-only code into a client component, which leaks it into the bundle or breaks the build.
- Using browser APIs during server rendering. Hydration mismatches from non-deterministic rendering (dates, random values).
- Adding `"use client"` high in the tree, which turns large subtrees into client code.
- Environment variables: only those with the public prefix reach the browser. Never prefix secrets.
- Installing a new auth, data-fetching, form, or styling library when one exists.

## Security

- Authorize inside every route handler and server action, not just in middleware or the UI. Middleware matchers can miss paths.
- Treat server action arguments as untrusted input.
- Avoid `dangerouslySetInnerHTML` unless the content is sanitized with the project's sanitizer.
- Cookie-based auth with route handlers that accept form posts needs CSRF consideration. Check what the auth library already provides.

## Performance

- Fetch in parallel on the server, and avoid client-side waterfalls.
- Keep client bundles small: heavy libraries in server components, `next/dynamic` for rarely used heavy client components.
- Use `next/image` and `next/font` if the project already does.
- Paginate data queries. Watch for N+1 through the ORM in server components.

## Testing

- Unit/component tests with the existing runner (Vitest or Jest) and Testing Library. Async Server Components are hard to unit test, so test their data functions directly and use E2E (Playwright/Cypress, if present) for full flows.
- Test server actions and route handlers as functions with mocked auth/session helpers, following neighbors.
- Run `typecheck`, `lint`, and `build` scripts. The build catches server/client boundary errors.
