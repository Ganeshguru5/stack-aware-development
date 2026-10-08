# Database

## Contents
- Identify database, access layer, and migration tool
- Schema design
- Migrations
- Queries and N+1
- Indexing
- Transactions and concurrency
- Connection management
- Engine notes: PostgreSQL, MySQL/MariaDB, SQLite, SQL Server, MongoDB, Redis
- Testing data access

## Identify database, access layer, and migration tool

Record all three separately, for example "PostgreSQL / SQLAlchemy 2 async / Alembic" or "MySQL / JPA (Hibernate) / Flyway". See [stack-detection.md](stack-detection.md). Each one constrains what you can write:

- Engine-specific SQL (`RETURNING`, `ON CONFLICT`, JSON operators, `LIMIT` syntax) must match the actual engine, including the engine used in tests. SQLite or H2 in tests while production runs PostgreSQL is a common source of false greens.
- Don't replace or bypass the data-access layer without a strong reason. Raw SQL is fine where the codebase already uses it for complex queries, through the same execution helper.

## Schema design

- Follow existing naming (table plural/singular, snake/camel columns, `id` vs `<table>_id`), key type (serial/identity, UUID, ULID), timestamp columns, and soft-delete conventions.
- Enforce integrity in the database where the project does: `NOT NULL`, foreign keys, unique constraints, check constraints. Application-only validation doesn't prevent races.
- Choose types deliberately: money as decimal/integer minor units (never float), timestamps with time zone semantics consistent with existing columns, bounded strings where the project bounds them.
- Model relationships the way the ORM in use expects (join tables, cascade rules). Be explicit about delete behavior.

## Migrations

- Use the existing migration tool and its naming/numbering scheme. Generate migrations with the tool where possible, then **review the generated SQL**.
- Never edit a migration that may already have run in a shared environment. Add a new one.
- Consider existing data:
  - Adding a `NOT NULL` column to a populated table needs a default or a backfill sequence: add nullable → backfill → add constraint.
  - Renames and type changes break running application versions. Use expand/contract (add new, dual-write or backfill, switch reads, remove old) for zero-downtime deployments.
  - Index creation on large tables can lock writes. Use the engine's online/concurrent option if the project supports it.
- Make migrations reversible if the tool and the project do down migrations.
- Keep ORM models/entities and migrations in sync, and run the tool's drift or check command if one exists.

## Queries and N+1

- **N+1**: a query per row inside a loop, or lazy relationship access during serialization. Detect it by enabling SQL logging in a test or locally and counting queries, or by reading loops that touch relationships. Fix it with the access layer's own mechanism: eager loading (`JOIN FETCH`/entity graphs, `selectinload`/`joinedload`, `include`/`with`, `Include`, `select_related`/`prefetch_related`, `Preload`), batching (`WHERE id IN (...)`), or a single joined query.
- Select only the columns you need for large rows or hot paths, as the codebase does.
- Push filtering, sorting, pagination, and aggregation into the database instead of loading everything into memory.
- Always parameterize. Never build SQL by string concatenation with input. Dynamic identifiers (sort columns) must come from an allowlist.
- Bound every query that returns lists.

## Indexing

- Index columns used in selective `WHERE`, `JOIN`, and `ORDER BY` clauses, and foreign keys (some engines don't index them automatically).
- Composite index column order matters: equality columns first, then range/sort columns. A composite index can serve queries on its leftmost prefix.
- Verify with the engine's plan output (`EXPLAIN`/`EXPLAIN ANALYZE`, the execution plan, `explain()` in MongoDB) on realistic data volume. A plan on an empty dev table proves little.
- Every index slows writes and uses storage. Don't add speculative indexes. Check for an existing index that already covers the query.
- An index that your change needs isn't speculative. If the change introduces a new filter, sort, or pagination order on a table that can grow, add the supporting index in the same change, as a new migration. If you couldn't verify it with a query plan, say so.

## Transactions and concurrency

- Use the project's transaction mechanism (declarative annotations, unit-of-work/session scope, explicit `BEGIN`/`COMMIT` helpers). Know where boundaries begin and end. In some frameworks, self-invocation or non-public methods silently skip declarative transactions.
- Multi-step writes that must be all-or-nothing belong in one transaction.
- Keep transactions short. No network calls to external services inside a DB transaction. Use an outbox or after-commit hook if the project has one.
- For read-modify-write races, use optimistic locking (version column), `SELECT ... FOR UPDATE`, atomic updates (`SET x = x + 1`), or unique constraints, matching the existing pattern.
- Handle unique-constraint violations as domain errors (for example 409), not 500s.

## Connection management

- Reuse the existing pool/engine/client. Never create a client per request.
- Respect pool size limits, especially with serverless/edge runtimes or many replicas. Use the project's pooler or proxy configuration.
- Make sure connections, cursors, and sessions are closed or returned (context managers, `defer`, `using`, try-with-resources, or framework-managed scope).

## Engine notes

**PostgreSQL**: rich types (`jsonb`, arrays, `uuid`, `timestamptz`). Use `timestamptz` if the project does. `CREATE INDEX CONCURRENTLY` can't run inside a transaction, so check the migration tool's support. `ON CONFLICT` for upserts. Partial and expression indexes are often the right tool for filtered queries. Check for row-level security policies before adding tenant filters by hand.

**MySQL/MariaDB**: storage engine should be InnoDB (needed for transactions and FKs). Use `utf8mb4` for full Unicode. Default isolation is REPEATABLE READ, which affects locking and gap locks. Online DDL support varies by operation and version, so check before altering big tables. Upserts use `INSERT ... ON DUPLICATE KEY UPDATE`. MariaDB and MySQL have diverged in places, so confirm which one is used.

**SQLite**: single writer, so expect `database is locked` under concurrent writes (WAL mode helps). Foreign keys are only enforced if `PRAGMA foreign_keys=ON`. Type affinity is loose, and `ALTER TABLE` is limited, so many changes need table rebuilds (migration tools usually handle this). Good for embedded/local apps and tests, but tests on SQLite don't prove behavior on a server database.

**SQL Server**: `IDENTITY`/sequences, `OFFSET ... FETCH` pagination (needs `ORDER BY`), `MERGE` has known pitfalls (prefer explicit patterns if the codebase does). Collation affects case sensitivity. Watch parameter-sniffing effects on plans.

**MongoDB**: schema lives in application code (Mongoose schemas, validators, ODM models) and optionally in collection validators. Follow it. Embed data that is read together and bounded in size, and reference unbounded or independently accessed data. Index fields used in filters and sorts (compound index order follows equality → sort → range). Multi-document transactions need a replica set and have costs, so prefer single-document atomic updates (`$set`, `$inc`). Never pass raw request objects as query filters (operator injection).

**Redis**: usually a cache, session store, rate limiter, queue, or lock, so find out which role it plays here. Always set TTLs on cache keys. Follow the existing key naming/prefix scheme. Avoid `KEYS` in production code (use `SCAN`). Data may be evicted or lost depending on config, so don't treat it as the source of truth unless the project does. Define cache invalidation alongside the write path.

## Testing data access

Use the project's existing strategy (Testcontainers/real DB in CI, transactional rollback, test schema, in-memory fakes). Test new queries against the same engine as production where the project supports it. For migrations, run them against a database with representative existing data when you can. Add a regression test for N+1 fixes by asserting the query count, if the project has a helper for it.
