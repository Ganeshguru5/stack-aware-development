# stack-aware-development

An [Agent Skill](https://agentskills.io) that makes coding agents inspect a repository's real technology stack and conventions before changing code. The agent then makes the smallest change that fits what's already there.

> Don't ask "what technology do I normally use?"
> Ask: "What is this repository already using, how is it structured, what conventions does it follow, and what is the smallest correct change I can make?"

## What is it?

Coding agents often make technology assumptions:

- The repository is Java + Spring Boot + PostgreSQL, but the agent answers with Node.js patterns.
- The repository uses Python + FastAPI, but the agent introduces Express-style concepts, or Django idioms.
- A Next.js app already has authentication, but the agent installs a different auth library.
- The repository uses pnpm, but the agent runs `npm install` and creates a second lockfile.

`stack-aware-development` adds a contextual layer to the agent's workflow. It detects the stack from evidence, learns the conventions from the closest existing code, loads only the guidance that's relevant, and verifies the change with the project's own commands.

## Why it exists

The model usually knows the right idioms. What goes wrong is that it doesn't check which idioms apply. Specialized skills (for a framework, a database, a testing tool) give deep knowledge, but only after someone has worked out that the repository uses that technology, at that version, in that package of the monorepo. This skill does that work first, and it makes the repository's existing patterns win over generic best practices unless there is a correctness, security, or compatibility reason to deviate.

## How it works

```
Inspect → Detect → Understand → Adapt → Implement → Verify
```

1. **Detect the stack** from lockfiles, manifests, config, imports, and CI, in that order of trust. Docs and READMEs are the weakest evidence. The database and the data-access layer are recorded separately, and in a monorepo detection is scoped to the package being changed. An optional bundled script (`scripts/detect_stack.py`) collects these signals deterministically.
2. **Learn the conventions** with the *nearest-neighbor* method: find the existing feature most like the requested one and copy its layering, validation, errors, response shape, and tests.
3. **Classify the task** (feature, bug fix, API, database, auth, performance, and so on; a task can have several categories) and load only the matching references plus the language and framework files for the detected stack.
4. **Plan the smallest correct change.** Reuse dependencies, respect boundaries, keep the diff focused, and flag contract changes.
5. **Implement** in the shape of the nearest neighbor, using the idioms of the installed version.
6. **Verify** with the project's own test, lint, type, and build commands, and report honestly what couldn't be run.
7. **Review** for correctness, security, performance, and compatibility, in proportion to the change.

The skill scales its effort to the task. A typo fix gets a glance at the surrounding code, not a stack analysis.

## Supported ecosystems

Support levels are stated conservatively.

| Level | Meaning | Ecosystems |
|-------|---------|------------|
| **Dedicated** | Language and framework reference files, detector rules, and written eval scenarios | Java/Kotlin + Spring Boot · TypeScript/JavaScript + Next.js/React, Express, Fastify, NestJS · Python + FastAPI, Django/DRF, Flask · Go + Gin, Echo, Fiber, Chi, `net/http` · C# + ASP.NET Core |
| **General** | Language file or notes, plus detector rules. Relies on repository evidence. | Rust (Axum, Actix, Rocket) · PHP (Laravel, Symfony) · Ruby (Rails, Sinatra) · Elixir, Dart/Flutter, Swift, Scala, C/C++ (notes only) · Vue, Nuxt, Angular, Svelte, Quarkus, Micronaut, Ktor (detected, no dedicated file) |
| **Planned (V2)** | Not yet covered | Dedicated files for Vue/Nuxt, Angular, Svelte, Laravel, Symfony, Rails, Quarkus/Micronaut, Ktor, Axum/Actix, mobile; infrastructure-as-code stacks |

**Databases:** PostgreSQL, MySQL/MariaDB, SQLite, SQL Server, MongoDB, and Redis have engine notes in `references/database.md`. Oracle is detected only.
**Data-access layers:** Prisma, Drizzle, TypeORM, Sequelize, Knex, Mongoose, JPA/Hibernate, Spring Data JDBC, jOOQ, MyBatis, JDBC, SQLAlchemy, Django ORM, EF Core, Dapper, pgx, sqlx, sqlc, GORM, ent, SQLx, Diesel, SeaORM, Eloquent, Doctrine, ActiveRecord, and raw SQL.

### Validation status

| Check | Status |
|-------|--------|
| Agent Skills spec (`skills-ref validate`) | Passes |
| Discovery by the `skills` CLI (`npx skills add . --list`) | Finds 1 skill from the repository root |
| `scripts/validate_skill.py` (frontmatter, links, orphans, TOCs, evals, hygiene) | Passes; negative tests confirmed it reports seeded errors |
| `scripts/detect_stack.py` unit tests (`tests/`, 14 cases across 9 ecosystems, lockfile-resolved versions, workspaces, decoys, `.env` privacy) | Pass; deliberately breaking the parser makes them fail |
| `scripts/detect_stack.py` on the 12 eval fixtures | Correct ecosystem and framework for all 12 (Clojure detected after a fix this run surfaced) |
| CI (`.github/workflows/validate.yml`) | Validator, unit tests, and `skills-ref` on Python 3.9 and 3.13. Not yet run on GitHub. |
| With vs. without the skill: 12 cases, 1 run each, 1 model, blind-graded | 98.0% vs. 94.1% of expectations; no failure conditions triggered in either. **Small effect, within noise.** See [evals/BENCHMARK.md](evals/BENCHMARK.md). |
| Multiple runs per case, multiple models, real toolchains | **Not yet run** |
| Trigger accuracy (`evals/trigger-evals.json`) | **Not yet run** |

## Examples

These examples describe the behavior that the corresponding eval cases check. The benchmark runs did this, except that no environment had toolchains, so tests were written but not executed.

**Java / Spring Boot**: "Add an endpoint to create users."
The agent detects Maven, Spring Boot 3, JPA, PostgreSQL, Flyway, and JUnit 5 + Mockito. It mirrors the existing `OrderController → OrderService → OrderRepository` package, uses a record DTO with Bean Validation, maps a duplicate email to 409 through the existing `@RestControllerAdvice`, adds a new Flyway migration, writes `@WebMvcTest` tests, and runs `./mvnw test`. It writes no Node concepts and adds no Lombok.

**TypeScript / Next.js**: "Add authentication."
The agent finds Auth.js already configured with a Prisma adapter. Instead of installing another library, it reports that authentication exists and identifies what's missing: unprotected routes and a hard-coded owner. It then enforces the session on the server in pages and route handlers, and tests that logic with Vitest through `pnpm`.

**Python / FastAPI**: "This endpoint is very slow. Fix it."
The agent traces router → service → repository, counts queries, finds lazy loading in a loop (N+1) and a missing index on the foreign key, fixes them with `selectinload` and a new Alembic migration, adds a query-count regression test, and runs `uv run pytest`. It doesn't add a cache before fixing the query.

**Go / Gin**: "Add pagination to the orders endpoint."
The agent finds that `/products` already uses keyset pagination with `?limit=&cursor=` and a `{data, meta}` envelope. It reuses the same parsing, validation, and cursor helpers for `/orders`, writes the pgx query with a deterministic `ORDER BY` and a tiebreaker, and adds table-driven tests. No ORM is introduced.

## Composition with other skills

This skill is responsible for **repository context and workflow**. Specialized skills are responsible for **depth in their domain**.

- If the agent environment already provides guidance for the detected technology (a Next.js, PostgreSQL, testing, or security skill, for example), this skill defers to it for domain-specific implementation details, and keeps applying the stack profile, conventions, minimal-change, and verification rules.
- If specialized guidance conflicts with the repository's established pattern, the repository wins, unless the guidance points to a correctness, security, or data-integrity problem.
- The skill **doesn't install or invoke other skills**. Whether several skills are active at once depends on the host agent. With no other skills present, the bundled references are the baseline.

## Installation

Verified against the current [skills CLI](https://github.com/vercel-labs/skills) and [skills.sh](https://skills.sh) documentation.

```bash
npx skills add Ganeshguru5/stack-aware-development
```

Useful flags: `-g` installs globally (user level), `-a claude-code` targets one agent, `-y` skips prompts. The CLI supports Claude Code, Cursor, Codex, GitHub Copilot, Gemini CLI, and many other agents.

**Manual (Claude Code):** copy or clone the repository to `~/.claude/skills/stack-aware-development/` (personal) or `.claude/skills/stack-aware-development/` (project). The directory name must be `stack-aware-development`.

### skills.sh listing

There's no submission form. Public GitHub repositories appear on the [skills.sh](https://skills.sh) leaderboard automatically, through the CLI's anonymous install telemetry, once people install them with `npx skills add`. To opt out of telemetry when installing, set `DISABLE_TELEMETRY=1` or `DO_NOT_TRACK=1`.

## Testing locally with Claude Code

1. Make the skill visible to Claude Code. Use either of these:
   ```bash
   npx skills add /path/to/stack-aware-development -a claude-code
   ```
   or link or copy the folder to `~/.claude/skills/stack-aware-development`. Claude Code picks up changes in existing skill directories without a restart. Run `/reload-skills` if you created a new top-level skills directory.
2. Build the eval fixture repositories somewhere outside the skill. Each one becomes its own git repository:
   ```bash
   python evals/build_fixtures.py unpack /tmp/sad-evals
   ```
3. Open a fixture (for example `/tmp/sad-evals/04-go-gin-pagination`) and give the matching case's `prompt` from `evals/evals.json`. Eval 8 is a review: its fixture has a `pr` branch to compare against `main`.
4. Check that the skill triggered (or invoke it explicitly with `/stack-aware-development <task>`), then grade the diff and report against the case's `expectations` and `failure_conditions`. To measure the skill, unpack a second copy and run the same prompt without the skill installed.
5. For trigger tuning, run the queries in `evals/trigger-evals.json` and check which ones activate the skill.

`evals/evals.json` follows the field layout the skill-creator tooling uses (`skill_name`, `evals[].id/prompt/expected_output/files/expectations`), extended with `scenario`, `repository`, `categories`, and `failure_conditions`. The fixture repositories are packed into `evals/fixtures.json` rather than stored as real files. Real `package.json` or `pom.xml` files inside an installed skill would become false stack signals for the host project.

### Benchmark

The first with/without comparison (12 cases, one run each, blind-graded) scored 74.5/76 expectations with the skill and 71.5/76 without. Neither condition triggered a failure condition. The skill came out slightly ahead in 6 cases, behind in 1, and tied in 5. Its clearest wins were on the stack with no dedicated guidance, on measurement habits, and on migration consistency.

The honest reading: on tidy repositories, a strong model already does most of what this skill teaches, so the effect is small and within noise. Methodology, per-case notes and next steps are in [evals/BENCHMARK.md](evals/BENCHMARK.md).

## Development

```text
stack-aware-development/
├── SKILL.md               # workflow, rules, routing table (always loaded on activation)
├── references/            # cross-cutting concerns, loaded per task category
├── languages/             # one file per language family + other.md fallback
├── frameworks/            # one file per framework family
├── scripts/
│   ├── detect_stack.py    # optional signal collector for agents (stdlib, read-only)
│   └── validate_skill.py  # maintainer check; run before every commit
├── evals/
│   ├── evals.json         # behavioral scenarios
│   ├── trigger-evals.json # should/should-not trigger queries
│   ├── fixtures.json      # packed fixture repositories, one per scenario
│   ├── build_fixtures.py  # unpack fixtures into git repos (or repack them)
│   └── BENCHMARK.md       # with/without-skill results and method
├── tests/                 # unit tests for detect_stack.py (stdlib unittest)
├── .github/workflows/     # CI: validator, unit tests, skills-ref
└── docs/DESIGN.md         # design note: landscape, gap, scope
```

Run the checks:

```bash
python scripts/validate_skill.py
```

```bash
python -m unittest discover -s tests
```

```bash
python scripts/detect_stack.py /path/to/some/repo
```

**Add a language:** create `languages/<language>.md` (with Contents, Detect, tooling, errors, testing, and verification commands sections), link it from the language list in `SKILL.md`, add manifest and lockfile rows to `references/stack-detection.md`, add `RULES`/`MANIFESTS` entries in `scripts/detect_stack.py`, and add a test case to `tests/test_detect_stack.py`.

**Add a framework:** create `frameworks/<framework>.md` (with sections for inspecting the app, patterns, pitfalls, security, performance, and testing), link it from the framework list in `SKILL.md`, add a row to the framework signals table, and add detector rules.

**Add a database or data-access layer:** add engine notes to `references/database.md` and detector rules for its drivers, ORMs, and migration tools.

**Add an eval:** append a case to `evals/evals.json` with a unique `id`, a concrete `repository` description, and observable `expectations` and `failure_conditions`. Test behavior, not keywords. Then build its fixture repository in a working folder named `NN-<case-name>/` (use `base/` and `pr/` subfolders for a review case), and repack all fixtures with `python evals/build_fixtures.py pack <folder>`. Don't put comments in fixtures that hint at the expected answer.

Contribution rules: keep `SKILL.md` under 500 lines, give reference files over 100 lines a `## Contents` section, keep links one level deep from `SKILL.md`, use only generic examples, include nothing proprietary, and never add project manifest files (`package.json`, `pom.xml`, and so on) anywhere in the skill.

## License

[MIT](LICENSE)
