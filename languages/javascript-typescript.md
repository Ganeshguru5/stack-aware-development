# JavaScript / TypeScript

## Contents
- Detect
- Package managers and scripts
- Module system
- Type safety
- Async and errors
- Frontend vs. backend vs. shared code
- Testing
- Verification commands

## Detect

- Runtime: Node (version from `.nvmrc`, `.node-version`, `engines`, `.tool-versions`), Bun (`bun.lock`), Deno (`deno.json`), browser-only, or edge runtimes (framework config or route-level runtime settings).
- TypeScript: `tsconfig.json` (check `strict`, `paths` aliases, `module`/`moduleResolution`, `target`), project references, or JS with JSDoc types.
- Framework files: [nextjs-react](../frameworks/nextjs-react.md) and [node-express-nest](../frameworks/node-express-nest.md).

## Package managers and scripts

- Use the package manager that matches the lockfile or the `packageManager` field. Never mix them: one lockfile per project.
- Add dependencies with that manager so the lockfile updates. Put runtime deps in `dependencies` and build/test tooling in `devDependencies`. In workspaces, add the dependency to the correct package, not the root, unless the repo does it that way.
- Run tasks through `package.json` scripts (`test`, `lint`, `typecheck`, `build`). They encode project flags.
- Check `node_modules` and lockfiles for what's actually installed before suggesting an API. Versions matter a lot in this ecosystem.

## Module system

- ESM (`"type": "module"`, `.mjs`, `import`) vs CommonJS (`require`, `.cjs`). Match the package. Don't mix within a file.
- Respect import conventions: path aliases (`@/…`), extensions in ESM imports where the setup requires them (`.js` suffix in TS ESM with NodeNext), barrel files, `import type` usage.

## Type safety

- Follow the project's strictness. Don't add `any`, `@ts-ignore`, or non-null assertions (`!`) to make errors disappear. Model types properly or narrow with type guards.
- Reuse existing types: generated API/ORM types, shared types packages, schema-inferred types (for example a type inferred from the project's validation schema).
- Validate untrusted input at runtime with the project's schema library. TypeScript types don't validate data at runtime.
- Keep the existing preference for `type` vs `interface`, enums vs union literals, and `null` vs `undefined`.

## Async and errors

- Always `await` or deliberately handle promises. Floating promises lose errors. Use `Promise.all` or `Promise.allSettled` for independent work, with bounded concurrency for large batches.
- Don't block the event loop with sync I/O (`fs.*Sync`, CPU-heavy loops) in request paths.
- Follow the project's error style: custom `Error` subclasses, error codes, Result objects, framework exceptions. Preserve causes (`new Error(msg, { cause })`) if the codebase does.
- Wrap or propagate errors to the framework's error handler instead of sending ad-hoc responses.

## Frontend vs. backend vs. shared code

- Know which environment each file runs in. Server-only code (DB access, secrets, Node APIs) must never be imported into client bundles. Browser APIs (`window`, `localStorage`) aren't available on the server or during SSR.
- Environment variables exposed to the browser need the framework's public prefix. Anything else is server-only and must never contain secrets that reach the client.
- In monorepos, shared packages should stay runtime-neutral unless they're explicitly server-only or client-only.

## Testing

- Use the existing runner (Jest, Vitest, Mocha, `node:test`, Bun test) and its config. Match `*.test.ts` vs `*.spec.ts` and the file location.
- Component tests with the project's library (for example Testing Library). E2E with the existing tool (Playwright, Cypress) only where the project already has E2E tests.
- HTTP mocking with the existing approach (MSW, nock, injected fakes).

## Verification commands

From package scripts, typically: type check (`tsc --noEmit` or a `typecheck` script), lint (ESLint/Biome), tests (filtered to the changed files first), build. Run them through the project's package manager, using workspace filters in monorepos.
