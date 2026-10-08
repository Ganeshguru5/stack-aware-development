# Code review

## Contents
- Scope and priorities
- Stack-aware review questions
- Writing findings

## Scope and priorities

Review the diff in the context of the repository, not in isolation. First build the stack profile and look at the nearest neighbors of the changed code, so that you judge it against this codebase's conventions instead of general preferences.

Report findings in this order:
1. **Correctness**: logic errors, unhandled error paths, null/empty cases, off-by-one, race conditions, wrong transaction boundaries, wrong async handling.
2. **Regressions and compatibility**: changed API contracts, removed fields, behavior changes for existing callers, migrations that break existing data or running versions, config default changes.
3. **Security**: see [security.md](security.md), applied proportionally to what the diff touches.
4. **Data and performance impact**: new N+1 queries, unbounded queries, missing indexes for new query shapes, heavy work on hot paths, large payloads.
5. **Error handling and observability**: errors mapped consistently, failures logged without leaking secrets.
6. **Test coverage**: are the new behavior and failure paths tested at the right level, and do bug fixes have regression tests?
7. **Consistency and maintainability**: does the change follow existing conventions, does it add redundant dependencies or new patterns, and is any complexity unjustified?

Style issues already covered by the project's formatter or linter aren't review findings. Subjective preferences that conflict with existing conventions aren't findings either.

## Stack-aware review questions

- Does the change use the same framework idioms, for the installed version, as the rest of the codebase?
- Was a dependency added that duplicates an existing one?
- Was the lockfile updated by the correct package manager?
- Are generated files changed by regenerating them from their source, rather than by hand?
- Do new migrations, schema changes, and model changes agree with each other?
- In a monorepo: are the changes confined to the right packages, with consistent cross-package versions?

## Writing findings

Each finding should state:
- **Where**: file and line.
- **What**: the concrete defect.
- **Impact**: a failure scenario (inputs or state → wrong result).
- **Fix**: a suggestion in the codebase's own style.

Separate "must fix" from "consider". Prefer a few high-confidence findings over a long list of speculative ones. If you're unsure whether something is a defect, say what would confirm it.
