# Architecture

## Contents
- Read the architecture before changing it
- Placing new code
- Coupling and boundaries
- Complexity budget
- Refactoring
- When the architecture blocks the task

## Read the architecture before changing it

Map the parts that the change touches. You don't need to map the whole system.

- **Entry points**: HTTP routes, CLI commands, message consumers, scheduled jobs, UI routes.
- **Layers or modules**: how a request flows from the entry point to storage and back.
- **Boundaries**: packages or modules that don't import each other, public vs. internal APIs, enforced rules (architecture tests such as ArchUnit, import-lint rules, Go `internal/`, Rust visibility, .NET project references).
- **Shared infrastructure**: DB session/connection handling, HTTP clients, auth context, configuration, logging.
- **Cross-cutting mechanisms**: middleware/filters/interceptors, event buses, background workers, caching layers.

Write the request path for the change in one line, for example `POST /orders → OrdersController → OrderService.create → OrderRepository.save → orders table`. If you can't write it, keep reading.

## Placing new code

- Put new code where its nearest neighbor lives. A new resource in a feature-folder codebase gets a new feature folder that looks like the existing ones.
- Business rules go in the layer where existing business rules live, not in controllers or templates, unless that's the established pattern.
- Reuse existing shared infrastructure (DB session, HTTP client, logger, config accessor) instead of creating a new instance.
- Respect dependency direction: if domain code doesn't import framework code today, don't make it start.

## Coupling and boundaries

Before adding a dependency between modules, check:
- Does module A already depend on B? If not, is there an existing interface, event, or shared package meant for this?
- Will the change create a cycle?
- Is the code you want to call internal or private to its module? If so, use or extend its public surface rather than reaching in.

For services that talk over the network, a change to a contract (API, message schema, shared DB table) is a cross-team change. Keep it backward compatible or flag it.

## Complexity budget

- Don't add an abstraction (interface, factory, strategy, generic base class) until there are at least two real implementations, unless the codebase already uses that abstraction for this kind of component. In that case, follow it.
- Prefer a direct implementation that matches the neighbors over a "more flexible" design nobody asked for.
- Don't add configuration options, plugin points, or feature flags that aren't required.
- Duplicating three lines is often better than a new shared helper that couples unrelated modules. Follow the codebase's existing tolerance for duplication.

## Refactoring

- Refactor only what the task needs, or what the user asked for.
- Keep behavior identical. Have tests in place first. Add characterization tests if coverage is missing for the code you're restructuring.
- Do structural changes and behavior changes as separate steps (and separate commits, if you're committing).
- For large refactors, propose a staged plan instead of one big diff.

## When the architecture blocks the task

Sometimes the requested change really doesn't fit, for example when there's no transaction boundary that spans the two writes, or no seam for injecting the dependency.

1. Explain the specific obstacle.
2. Propose the smallest structural change that unblocks the task.
3. If it's significant, confirm with the user before proceeding.
4. Implement it in the style of the existing code.
