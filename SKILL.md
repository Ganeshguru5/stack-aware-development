---
name: stack-aware-development
description: Inspects an existing repository before changing code. Detects its actual languages, frameworks, databases, data-access layers, test tools, and conventions from manifests, lockfiles, config, and source, then plans and implements the smallest change that fits that stack instead of defaulting to familiar technologies. Use when implementing features, fixing bugs, debugging, refactoring, improving performance, changing APIs, schemas or migrations, or adding authentication, authorization, or tests in an existing codebase, especially unfamiliar, polyglot, or monorepo projects (for example Java/Kotlin with Spring, TypeScript with Next.js or Node, Python with FastAPI or Django, Go, C#/.NET, Rust, PHP, Ruby). Also use when reviewing a change for consistency with the existing architecture. Not for choosing a stack for a new project, standalone snippets, or questions that do not involve a repository.
license: MIT
metadata:
  version: "1.0.0"
---

# Stack-Aware Development

Don't ask "what technology do I normally use?" Ask:

> What is this repository already using, how is it structured, what conventions does it follow, and what is the smallest correct change I can make?

Detect first. Understand second. Adapt third. Implement fourth. Verify last.

## Contents

- Scale the effort
- Workflow
- Step 1: Detect the stack
- Step 2: Learn the conventions
- Step 3: Classify the task and load references
- Step 4: Cooperate with specialized skills
- Step 5: Plan the smallest correct change
- Step 6: Implement
- Step 7: Verify
- Step 8: Review
- Report
- Rules
- Red flags
- Reference index

## Scale the effort

Match the depth of investigation to the size and risk of the change.

| Change | Inspection depth |
|--------|------------------|
| Typo, copy change, one-line fix in a file you already have open | Glance at the surrounding code and match it. Skip the stack profile. |
| Small feature or bug fix in one module | Write a short stack profile, find one nearest-neighbor example, run the relevant tests. |
| Cross-cutting change: auth, schema/migration, public API, dependency, performance, multiple modules | The full workflow below. |

Skipping inspection is never acceptable when the next step would add a dependency, a new pattern, a new directory convention, or a schema change.

## Workflow

Copy this checklist into your working notes for non-trivial tasks:

```
Stack-aware progress:
- [ ] 1. Detect: stack profile with evidence (scoped to the package being changed)
- [ ] 2. Conventions: nearest-neighbor example(s) identified
- [ ] 3. Classify task; load only the relevant references
- [ ] 4. Note any specialized skills available for this stack/concern
- [ ] 5. Plan the smallest correct change; list any deviations with reasons
- [ ] 6. Implement following the neighbor's shape
- [ ] 7. Verify with the project's own test/lint/type/build commands
- [ ] 8. Proportional review: correctness, security, performance, compatibility
- [ ] Report: stack, pattern followed, changes, verification, deviations
```

Never go straight from the request to editing code in an unfamiliar repository.

## Step 1: Detect the stack

Collect evidence, then write a short stack profile. Rank evidence from strongest to weakest:

1. **Lockfiles and resolved dependency manifests**: what is actually installed, and which version.
2. **Build and config files**: framework config, ORM config, test config, Docker/compose, CI workflows.
3. **Source imports and entry points**: what the code actually uses.
4. **Directory layout and file extensions.**
5. **README and docs**: weakest. They are often stale or aspirational.

Never conclude the stack from one file when stronger evidence is available. A name mentioned in a README, or an unused dependency, doesn't mean the framework is in use.

To collect signals quickly, you can run the bundled detector (Python 3.9+, standard library only, read-only):

```bash
python scripts/detect_stack.py <repo-root>
```

Use the path to this skill's directory. Its output is evidence to confirm, not a verdict. If Python isn't available, inspect manually. See [references/stack-detection.md](references/stack-detection.md) for the manifest-to-stack table, monorepo handling, and how to tell a database apart from its data-access layer.

**Stack profile**: keep it short:

```
Scope:        <package/service being changed, e.g. services/orders>
Language:     <language + version>       evidence: <file>
Framework:    <framework + major version> evidence: <file>
Data:         <database> via <ORM/driver>  evidence: <file>
Build/pkg:    <tool>                       evidence: <lockfile/build file>
Tests:        <framework + runner command> evidence: <config/CI>
Unknowns:     <what could not be determined>
```

Record the **major version** of the framework and language. Idioms change between major versions (for example, router models, namespace migrations, async APIs). Follow the idioms of the installed version, not the newest one you know about.

**Monorepos:** detect per package or service. The stack of the directory you're changing is what matters, not the root's.

## Step 2: Learn the conventions

The most reliable technique is the **nearest neighbor**. Find the one or two existing features most similar to the one you're about to change, and copy their shape: file placement, layering, naming, validation, error handling, response format, logging, and tests.

Examples:
- New endpoint → the most similar existing endpoint and its test.
- New table/column → the most recent migration and the model/entity it touched.
- New UI page → a sibling page with similar data loading.

Also check, when relevant: dependency injection style, configuration and secrets handling, auth middleware and permission checks, transaction boundaries, test fixtures and factories, lint/format configuration, and how existing tests are named and located.

When neighbors disagree, prefer the more recent and more common pattern, and say which one you followed. See [references/conventions.md](references/conventions.md) for a convention inventory and how to resolve conflicts.

## Step 3: Classify the task and load references

A task can belong to several categories. For example, "fix the slow orders endpoint and add pagination" is **API + performance + database + feature**.

Load **only** the references the categories call for, plus the language file and, if one exists, the framework file for the detected stack. Every task starts from stack detection (Step 1).

| Category | Load |
|----------|------|
| Feature | [architecture](references/architecture.md), [testing](references/testing.md); plus [api-design](references/api-design.md) / [database](references/database.md) if touched |
| Bug fix / debugging | [debugging](references/debugging.md), [testing](references/testing.md); [database](references/database.md) if data-related |
| Refactor | [architecture](references/architecture.md), [testing](references/testing.md) |
| API change / integration | [api-design](references/api-design.md), [testing](references/testing.md); [security](references/security.md) if externally exposed |
| Database change / migration | [database](references/database.md), [testing](references/testing.md) |
| Authentication | [authentication](references/authentication.md), [authorization](references/authorization.md), [security](references/security.md), [testing](references/testing.md) |
| Authorization / permissions | [authorization](references/authorization.md), [security](references/security.md), [testing](references/testing.md) |
| Performance | [performance](references/performance.md), [database](references/database.md) if data-bound, [testing](references/testing.md) |
| Security fix / hardening | [security](references/security.md), [testing](references/testing.md) |
| Testing only | [testing](references/testing.md) |
| Code review | [code-review](references/code-review.md) |
| UI/frontend | the framework file; [performance](references/performance.md) if rendering or bundle concerns are involved |
| Dependency update | [stack-detection](references/stack-detection.md) (lockfiles, package manager), [testing](references/testing.md), [security](references/security.md) |
| Infrastructure / CI | [stack-detection](references/stack-detection.md); follow existing pipeline and container conventions |
| Documentation | none beyond the conventions of the existing docs |

**Language files:** [JavaScript/TypeScript](languages/javascript-typescript.md) · [Java/Kotlin](languages/java-kotlin.md) · [Python](languages/python.md) · [Go](languages/go.md) · [C#/.NET](languages/csharp.md) · [Rust](languages/rust.md) · [Other languages](languages/other.md)

**Framework files:** [Next.js/React](frameworks/nextjs-react.md) · [Node: Express/Fastify/NestJS](frameworks/node-express-nest.md) · [Spring Boot](frameworks/spring-boot.md) · [FastAPI/Django/Flask](frameworks/fastapi-django.md) · [ASP.NET Core](frameworks/dotnet.md) · [Go web](frameworks/go-web.md)

**No dedicated file for the detected stack?** Use [languages/other.md](languages/other.md) and the codebase itself. Say plainly which parts of the stack you have no specific guidance for, rely on the repository's own patterns and docs, and don't borrow idioms from a different framework.

## Step 4: Cooperate with specialized skills

This skill owns **repository context and the overall workflow**. Specialized skills own **depth in their own domain**.

- If the environment already provides guidance for the detected technology or concern (for example a framework, database, testing, security, or UI skill), defer to it for domain-specific implementation details. Keep applying this skill's stack profile, conventions, minimal-change, and verification rules.
- If specialized guidance conflicts with what the repository already does, prefer the repository's established pattern, unless the specialized guidance identifies a correctness, security, or data-integrity problem. In that case, follow it and explain the deviation.
- Don't claim to install, invoke, or load other skills unless the host environment actually does so. When no specialized guidance is present, the references here are the baseline.
- Feed specialized guidance the right context: the detected version, the existing pattern, and the constraints. Generic advice applied to the wrong version is a common failure.

## Step 5: Plan the smallest correct change

- **Reuse before adding.** Before adding a dependency, search the manifest and the code for something that already does the job (validation, HTTP client, date handling, auth, logging, test utilities). Add a dependency only when nothing suitable exists. Then use the project's package manager and lockfile, and explain why.
- **Fit the existing architecture.** If the code uses `controller → service → repository`, add to those layers. Don't introduce a new layering scheme, folder convention, or pattern for one feature.
- **Keep the diff focused.** Touch only the files the change requires. No drive-by reformatting, renaming, or "while I'm here" refactors. Mention those as follow-ups instead.
- **Contract changes are explicit.** For public API, schema, event, or config changes, plan for backward compatibility or state clearly that the change is breaking.

Deviating from an existing convention is justified only by: a security problem, a correctness problem, a serious measured performance problem, a clear maintainability problem the task can't work around, an explicit user requirement, a compatibility requirement, or an architecture that actually blocks the requested change. Name the reason whenever you deviate.

For a large or risky change, share the plan (files to touch, pattern to follow, any dependency or migration) before implementing.

## Step 6: Implement

- Mirror the nearest neighbor: same layers, naming, validation mechanism, error types, response envelope, logging calls, and test style.
- Use the language and framework idioms of the **detected version**.
- Handle failure paths the way the code already does: same exception and error types, same status mapping, same error envelope.
- Don't leave TODOs for required behavior, stubbed security checks, or commented-out code.

## Step 7: Verify

Find the project's own commands instead of guessing them. Look in the package scripts, Makefile/justfile/Taskfile, build tool tasks, CI workflow files, `CONTRIBUTING`, and README. CI is usually the most reliable source.

1. Run the narrowest relevant tests first (the new or changed tests, then the affected module).
2. Run the static checks the project uses: type check, linter, formatter check, compile/build.
3. Run broader tests if the change crosses module boundaries or touches shared code.
4. If something can't run (missing services, credentials, network), say exactly what wasn't verified and why. Don't claim success.

Add or update tests at the level the project already tests at. A bug fix gets a regression test that fails without the fix.

## Step 8: Review

Before reporting, review your own diff with proportional depth. See [references/code-review.md](references/code-review.md).

- **Correctness**: edge cases, null/empty, error paths, concurrency, transaction boundaries.
- **Security**: when the change touches input, auth, data access, files, outbound requests, or secrets. See [references/security.md](references/security.md).
- **Performance**: when the change touches queries, loops over data, hot paths, or payload size.
- **Compatibility**: API contracts, migrations on existing data, config defaults.
- **Consistency**: does the change look like the rest of the codebase?

## Report

End with a concise summary:

```
Stack: <one line, with key evidence>
Followed: <the existing pattern/example mirrored, e.g. "OrderController/OrderService">
Changed: <files and what changed>
Verified: <commands run and results; anything not verified and why>
Deviations: <any departure from existing conventions and the reason, or "none">
Follow-ups: <optional; issues noticed but intentionally not changed>
```

## Rules

1. **Inspect before changing.** Don't start editing before you understand the relevant code.
2. **Detect before assuming.** Determine the stack from repository evidence, never from habit.
3. **Preserve existing conventions** unless one of the listed deviation reasons applies.
4. **Minimize unnecessary changes.** Leave unrelated files alone.
5. **Reuse existing dependencies.** No redundant libraries.
6. **Don't rewrite working architecture.** A new task isn't a reason for a rewrite.
7. **Don't impose personal preferences.** The repository's conventions outrank your preferred stack.
8. **Verify** with the project's own checks, and report honestly what couldn't be verified.
9. **Review the change** for correctness, security, performance, and maintainability.
10. **Explain meaningful deviations** from existing patterns.

## Red flags

Stop and re-check the stack profile if you're about to:

- Use a package manager that doesn't match the lockfile (for example `npm install` next to `pnpm-lock.yaml`, or `pip install` in a Poetry/uv project).
- Add a second library for something the project already does: validation, ORM, HTTP client, test framework, auth, logging, state management.
- Write a framework's idioms into a different framework (Express middleware in a Spring app, Django patterns in FastAPI, Pages Router APIs in an App Router project).
- Create a new top-level directory, layer, or naming pattern.
- Hand-edit a generated file or an already-applied migration.
- Introduce a new response or error format next to an existing one.
- Change public API shapes, database schemas, or default config values without mentioning compatibility.

## Reference index

Cross-cutting (load per Step 3): [stack-detection](references/stack-detection.md) · [conventions](references/conventions.md) · [architecture](references/architecture.md) · [api-design](references/api-design.md) · [authentication](references/authentication.md) · [authorization](references/authorization.md) · [database](references/database.md) · [testing](references/testing.md) · [debugging](references/debugging.md) · [security](references/security.md) · [performance](references/performance.md) · [code-review](references/code-review.md)
