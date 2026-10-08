# Performance

## Contents
- Measure before optimizing
- Where to look
- Fixes in order of preference
- Caching
- Frontend performance
- Verifying an improvement

## Measure before optimizing

1. **Define the symptom**: which operation, how slow, at what data volume or concurrency, and since when.
2. **Reproduce and measure** with the stack's tools: existing APM/tracing, request timing logs, SQL logging with timings, `EXPLAIN ANALYZE`, profilers (language profilers, flame graphs), browser performance tools and bundle analyzers.
3. **Find where the time goes**: DB, network, CPU, serialization, locks, or the client. Optimize the biggest contributor first.
4. **Change one thing at a time** and measure again.

If measurement isn't possible in the environment, reason from code evidence (query counts in loops, unbounded fetches, missing indexes for obvious filters), and label the conclusion as "likely" rather than measured.

## Where to look

| Symptom | Common causes |
|---------|---------------|
| Slow list/detail endpoint | N+1 queries, missing index, unbounded result set, fetching large columns, serialization of deep object graphs, lazy loading during serialization |
| Slow under load only | Pool exhaustion, lock contention, blocking calls in async code, synchronous external calls, missing timeouts |
| High memory | Loading whole tables/files into memory, unbounded caches, retained references, large payloads |
| High CPU | Inefficient algorithms (quadratic loops over collections), regex backtracking, repeated parsing/serialization, excessive logging |
| Slow page | Large bundles, render waterfalls, unnecessary re-renders, unoptimized images, client-side fetching that could happen on the server |

Async pitfalls by stack: blocking I/O inside an event loop (Node, Python async), sync-over-async deadlocks or thread starvation (.NET), blocking calls on reactive threads (reactive Java), unbounded goroutines without backpressure (Go).

## Fixes in order of preference

1. **Do less work**: remove redundant queries and calls, select fewer columns, paginate, filter in the database.
2. **Fix access patterns**: eager loading or batching for N+1, a single joined/aggregated query, bulk operations.
3. **Indexes**: add an index that matches the query shape, verified with the plan (see [database.md](database.md)).
4. **Concurrency**: run independent I/O in parallel with the stack's primitives, with bounded concurrency.
5. **Caching**: only after the above, with a clear invalidation strategy.
6. **Architecture changes** (async jobs, read models, denormalization): propose them, don't impose them.

Keep the existing architecture. A performance fix shouldn't swap the ORM, framework, or serialization library without measured evidence and the user's agreement.

## Caching

- Reuse the existing cache (in-process, Redis, HTTP caching, framework cache). Don't add a new cache technology for one endpoint.
- Define the key (including user/tenant scope where data is user-specific), the TTL, and invalidation on writes.
- Watch for stampedes on hot keys, and for stale data that breaks correctness.

## Frontend performance

- Check the framework's rendering model (server vs. client rendering, static vs. dynamic) before moving work around.
- Reduce shipped JavaScript: avoid heavy client-only dependencies, use dynamic imports for rarely used heavy components, and keep server-only code out of client bundles.
- Avoid request waterfalls by fetching in parallel or higher in the tree, as the framework recommends.
- Memoize only when profiling shows unnecessary re-renders, or when the codebase already does so consistently.
- Use the framework's image and font optimization if the project uses it.

## Verifying an improvement

- Compare before and after numbers under the same conditions, and report them.
- Add a regression guard where practical: a query-count assertion, a test against a larger fixture, or a benchmark if the project has a benchmark suite.
- Confirm that behavior is unchanged (same results, ordering, and pagination semantics).
