# Debugging

## Contents
- Process
- Stack-aware evidence sources
- Locating the failing boundary
- Fixing
- Anti-patterns

## Process

```
Reproduce → Observe → Collect evidence → Locate failing boundary
→ Form hypothesis → Test hypothesis → Fix root cause
→ Add regression test → Verify
```

1. **Reproduce**: get a reliable reproduction, ideally as a failing automated test, otherwise as a precise command or request. Note the inputs, environment, and versions.
2. **Observe**: read the full error, stack trace, and logs. The first error is usually more informative than the last.
3. **Collect evidence**: relevant code paths, recent changes (`git log`/`git diff` for the area, dependency bumps in the lockfile), config differences between environments, data that triggers the issue.
4. **Locate the failing boundary**: find the point where correct state turns into incorrect state (see below).
5. **Hypothesize**: state one specific, falsifiable cause.
6. **Test the hypothesis**: add a targeted log or assertion, run a debugger, write a narrower test. Confirm or reject it before changing code.
7. **Fix the root cause**, not the symptom.
8. **Add a regression test** that fails without the fix.
9. **Verify**: run the reproduction, the new test, and the related suite. Remove temporary instrumentation.

## Stack-aware evidence sources

- **Stack traces**: learn the shape of the stack's traces. Framework frames hide the application frame that matters. Check the "Caused by" chain in JVM traces, the bottom of the traceback in Python, wrapped error chains in Go (`%w`), and async stack gaps in JS/.NET.
- **Logs**: use the project's logger and levels. Check for request/correlation IDs to follow one request across services.
- **SQL**: enable the access layer's query logging (ORM echo/show-SQL settings, debug loggers) to see the actual queries and parameters.
- **HTTP**: capture the actual request and response (status, headers, body) at the boundary.
- **Runtime state**: the language's debugger, REPL, or a focused test with assertions.
- **Configuration**: effective config often differs from the files you're reading (profiles, env vars, overrides). Check how the framework resolves configuration.

## Locating the failing boundary

Walk the request path (entry → validation → business logic → data access → external calls → serialization) and check the data at each boundary. Bisect: check the middle first, then halve the search space. For regressions with a known good version, use `git bisect` or compare dependency versions.

Common boundary failures: serialization casing or format mismatches, time zone conversion, null versus missing, transaction not committed or rolled back, stale cache, async work not awaited, concurrency/races, environment-specific config, dependency version changes.

## Fixing

- Fix the code at the faulty boundary, not where the symptom appears.
- Look for the same bug pattern elsewhere. Mention other occurrences, and fix them only if they're in scope.
- Keep the fix minimal and in the codebase's style.
- If the root cause is upstream (a library bug, an infrastructure issue), document it and apply the narrowest workaround, with a comment linking to the cause.

## Anti-patterns

- Changing code at random until the error goes away.
- Catching and swallowing the exception, or adding null checks that hide the real problem.
- Adding retries or sleeps to "fix" race conditions.
- Bumping or swapping dependencies without evidence that they're the cause.
- Declaring it fixed without reproducing the failure first and confirming it after.
