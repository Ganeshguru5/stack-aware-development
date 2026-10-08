# Learning repository conventions

## Contents
- The nearest-neighbor method
- Convention inventory
- Resolving conflicting conventions
- When to deviate
- Examples of preserving conventions

## The nearest-neighbor method

1. Describe the change in one sentence ("add a POST endpoint that creates a user and persists it").
2. Search for the most similar existing feature by route, entity, or file-name pattern, or by a distinctive call such as the ORM's save method or the router's registration call.
3. Read it end to end: entry point → business logic → data access → tests.
4. List its decisions (inventory below) and make the same ones.
5. If there's no close neighbor, use the closest one at each layer (one example of a controller, one service, one repository, one test).

Searching is cheap. Read real files instead of guessing from directory names.

## Convention inventory

Check the items relevant to the change:

| Concern | What to look for |
|---------|------------------|
| Directory structure | Layered (`controllers/`, `services/`) vs. feature/domain folders (`orders/`, `users/`); where tests live (co-located vs. a mirrored `test/` tree) |
| Naming | File naming (kebab, snake, Pascal), class/function suffixes (`*Service`, `*Repository`, `*Handler`, `use*`), test naming (`*_test.go`, `test_*.py`, `*.spec.ts`, `*Tests.cs`) |
| Imports/modules | Path aliases (`@/`), absolute vs. relative, barrel files, package-private visibility, module boundaries enforced by lint rules |
| Layering | `controller → service → repository`, handlers calling the DB directly, CQRS, hexagonal ports/adapters. Copy whichever is used. |
| Validation | Schema library or framework mechanism (Zod/Yup/Valibot/class-validator, Bean Validation, Pydantic, Django forms/serializers, FluentValidation/DataAnnotations, struct tags with a validator) and where it runs |
| Errors | Custom exception/error types, error codes, global handlers (`@ControllerAdvice`, exception middleware, error boundaries), wrapping style (`fmt.Errorf("...: %w")`), Result types |
| API responses | Envelope (`{data, error}`, RFC 9457 problem details, bare objects), casing (camel/snake), pagination shape, date format |
| Auth | Middleware/guards/filters/decorators, how the current user is accessed, how permissions are checked |
| Data access | Repository classes, active record, query builders, raw SQL files, transaction helpers, soft deletes, audit columns |
| Logging/observability | Logger library and how it's obtained, structured fields, correlation/request IDs, metrics/tracing calls |
| Configuration | Env vars vs. config files, typed config objects, how secrets are loaded, feature flags |
| Dependency injection | Framework container, constructor injection, manual wiring in `main`, module registration |
| State (frontend) | Server components vs. client state, query/cache library, global store, form library |
| Tests | Unit vs. integration split, fixtures/factories, mocking library, test DB strategy (containers, in-memory, transactions rolled back), snapshot use |
| Style | Formatter/linter config is authoritative. Don't hand-format against it. |

## Resolving conflicting conventions

- Prefer the pattern used by the **most recent** and **most numerous** examples near the code you're changing.
- Prefer patterns enforced by tooling (lint rules, architecture tests, CI checks) over ones that are merely common.
- Documented conventions (`CONTRIBUTING`, ADRs, `AGENTS.md`/`CLAUDE.md`, a style guide) win over inference, as long as the code shows they're still followed.
- Within a single file, stay consistent with that file.
- State which convention you followed when the choice wasn't obvious.

## When to deviate

Only for: a security problem, a correctness problem, a serious measured performance problem, a clear maintainability problem the task can't avoid, an explicit user requirement, a compatibility requirement, or an architecture that blocks the requested change.

When you deviate:
- Keep the deviation local to the code the task requires.
- Explain it in the final report.
- Don't migrate other existing code to the new pattern unless asked.

## Examples of preserving conventions

| Repository already uses | Don't introduce |
|-------------------------|-----------------|
| `controller → service → repository` | `handler → use-case → gateway → adapter` for one feature |
| Zod for validation | Yup, Joi, or hand-rolled validation |
| JUnit 5 + Mockito | TestNG, Spock, or MockK in a Java module |
| Prisma | Drizzle, TypeORM, or raw `pg` queries alongside it |
| SQLAlchemy 2.x `select()` style | Legacy `session.query()` style, or the reverse |
| `errors.Is`/`%w` wrapping in Go | `github.com/pkg/errors` |
| An existing auth module/provider | A new auth library |
| Problem-details error responses | A new `{success:false}` envelope |
