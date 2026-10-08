# Stack detection

## Contents
- Procedure
- Directories to ignore
- Language and package manager signals
- Framework signals
- Database vs. data-access layer
- Test, build, and tooling signals
- Monorepos and polyglot repositories
- Conflicting or weak evidence
- Version awareness

## Procedure

1. List the top level of the repository and the directory you're about to change.
2. Find manifests and lockfiles (tables below). Read the manifest that is closest to the code being changed.
3. Read declared dependencies and identify frameworks, data-access libraries, and test tools.
4. Confirm by reading one or two entry points and a representative source file. Check imports, bootstrapping, and how routing and DI are wired.
5. Check runtime context: Dockerfile, compose files, CI workflows, `.env.example`, config files. These show the databases, services, and commands that are actually used.
6. Write the stack profile (see SKILL.md) with the evidence file for each claim, and list what is still unknown.

`scripts/detect_stack.py <root>` automates steps 2–3 and part of step 5. Always confirm its output against source code.

## Directories to ignore

Never use files under these directories as evidence for the host project: dependency and build output (`node_modules`, `vendor`, `.venv`, `venv`, `target`, `build`, `dist`, `out`, `bin`, `obj`, `.next`, `.nuxt`, `__pycache__`, `.gradle`, `.terraform`), and **agent tool and skill directories** (`.claude`, `.agents`, `.cursor`, `.codex`, `.github/skills`, and similar). Skills and plugins installed there may contain manifests and examples that have nothing to do with the project.

## Language and package manager signals

| Ecosystem | Manifest | Lockfile → package manager | Notes |
|-----------|----------|----------------------------|-------|
| JavaScript/TypeScript | `package.json` | `package-lock.json` → npm; `pnpm-lock.yaml` → pnpm; `yarn.lock` → Yarn (check `.yarnrc.yml` for Berry/PnP); `bun.lock`/`bun.lockb` → Bun | `packageManager` field in package.json is authoritative. `tsconfig.json` or `.ts` sources → TypeScript. `"type": "module"` → ESM. `deno.json` → Deno. |
| Java/Kotlin | `pom.xml` → Maven; `build.gradle(.kts)` + `settings.gradle(.kts)` → Gradle | Wrapper scripts `mvnw` / `gradlew` | Use the wrapper if it exists. `.kts` build or `src/main/kotlin` → Kotlin. `gradle/libs.versions.toml` = version catalog. |
| Python | `pyproject.toml`, `requirements*.txt`, `setup.py`/`setup.cfg`, `Pipfile` | `uv.lock` → uv; `poetry.lock` → Poetry; `Pipfile.lock` → Pipenv; `pdm.lock` → PDM; none → pip | In `pyproject.toml`, `[tool.poetry]`, `[tool.uv]`, `[tool.pdm]`, `[tool.hatch]` identify the tool. |
| Go | `go.mod` | `go.sum` | The `go` directive gives the language version. `go.work` → multi-module workspace. |
| Rust | `Cargo.toml` | `Cargo.lock` | `[workspace]` → multi-crate workspace. `rust-toolchain(.toml)` pins the toolchain. |
| C#/F#/.NET | `*.csproj`, `*.fsproj`, `*.sln`/`*.slnx` | `packages.lock.json` (optional) | `TargetFramework` gives the .NET version. `Directory.Packages.props` → central package management. `global.json` pins the SDK. |
| PHP | `composer.json` | `composer.lock` | `artisan` → Laravel; `bin/console` + `config/bundles.php` → Symfony. |
| Ruby | `Gemfile` | `Gemfile.lock` | `config/application.rb` → Rails; `config.ru` alone → Rack/Sinatra-style. |
| Others | `mix.exs` (Elixir), `pubspec.yaml` (Dart/Flutter), `Package.swift` (Swift), `build.sbt` (Scala), `deps.edn`/`project.clj` (Clojure), `CMakeLists.txt`/`meson.build` (C/C++), `*.cabal`/`stack.yaml` (Haskell) | Corresponding lockfiles | See [languages/other.md](../languages/other.md). |

Version pins: `.nvmrc`, `.node-version`, `.python-version`, `.tool-versions` (asdf/mise), `.java-version`, `.sdkmanrc`, `engines` in package.json, `requires-python`, `<java.version>` / toolchain blocks.

## Framework signals

Confirm with dependency evidence **and** source or config evidence.

| Framework | Dependency evidence | Source/config evidence |
|-----------|--------------------|------------------------|
| Next.js | `next` | `next.config.*`; `app/` (App Router) and/or `pages/` (Pages Router), possibly under `src/` |
| React (SPA) | `react`, `react-dom` without a meta-framework | `vite.config.*`, `index.html` entry; check for Remix/React Router framework mode, Gatsby, Expo |
| Vue / Nuxt | `vue` / `nuxt` | `*.vue`, `nuxt.config.*` |
| Angular | `@angular/core` | `angular.json` |
| Svelte / SvelteKit | `svelte` / `@sveltejs/kit` | `svelte.config.*` |
| Express / Fastify / Koa / Hono | `express` / `fastify` / `koa` / `hono` | `app.use(...)`, `fastify.register(...)` |
| NestJS | `@nestjs/core` | `*.module.ts`, `@Controller` decorators, `nest-cli.json` |
| Spring Boot | `spring-boot-starter-*`, `org.springframework.boot` plugin/parent | `@SpringBootApplication`, `application.yml/properties` |
| Quarkus / Micronaut | `io.quarkus` / `io.micronaut` | `application.properties` with `quarkus.` keys / `micronaut-cli.yml` |
| Jakarta EE | `jakarta.*` APIs with `war` packaging | `web.xml`, `beans.xml` |
| Ktor | `io.ktor` | `Application.module()` |
| FastAPI | `fastapi` | `FastAPI()` instance, `APIRouter` |
| Django | `django` | `manage.py`, `settings.py`, `INSTALLED_APPS` |
| Flask | `flask` | `Flask(__name__)`, blueprints |
| Litestar | `litestar` | `Litestar(route_handlers=...)` |
| Gin / Echo / Fiber / Chi | `github.com/gin-gonic/gin`, `github.com/labstack/echo`, `github.com/gofiber/fiber`, `github.com/go-chi/chi` | router construction in `main.go` or `cmd/` |
| Go stdlib HTTP | no router dependency | `http.NewServeMux`, `http.HandleFunc` |
| ASP.NET Core | `Microsoft.NET.Sdk.Web` SDK | `Program.cs` with `WebApplication.CreateBuilder`; `Controllers/` or minimal APIs |
| Blazor | `Microsoft.AspNetCore.Components.*` | `*.razor` |
| Laravel / Symfony | `laravel/framework` / `symfony/framework-bundle` | `artisan` / `bin/console` |
| Rails / Sinatra | `rails` / `sinatra` | `config/routes.rb` / `Sinatra::Base` |
| Axum / Actix / Rocket | `axum` / `actix-web` / `rocket` | `Router::new()` / `HttpServer::new` / `#[launch]` |

A framework that appears only in the README, a comment, or an unused dependency isn't evidence that it's in use.

## Database vs. data-access layer

These are **independent**. Record both, for example "PostgreSQL via Prisma" or "MySQL via raw JDBC and jOOQ".

**Database evidence:** driver packages (`pg`, `postgres`, `psycopg`, `asyncpg`, `mysql2`, `mysqlclient`, `PyMySQL`, `org.postgresql:postgresql`, `com.mysql:mysql-connector-j`, `mariadb-java-client`, `Microsoft.Data.SqlClient`, `Npgsql`, `go-sql-driver/mysql`, `jackc/pgx`, `mattn/go-sqlite3`, `modernc.org/sqlite`, `mongodb`, `pymongo`, `redis`/`ioredis`, `oracledb`/`ojdbc`), connection URL schemes in config or `.env.example` (`postgres://`, `mysql://`, `mongodb://`, `redis://`, `jdbc:...`), compose service images, Prisma `datasource provider`, Django `DATABASES['ENGINE']`, `spring.datasource.url`, EF Core provider packages.

**Data-access evidence:**

| Ecosystem | Layer and signal |
|-----------|------------------|
| JS/TS | Prisma (`prisma/schema.prisma`), Drizzle (`drizzle.config.*`), TypeORM (`@Entity`, `DataSource`), Sequelize, MikroORM, Kysely, Knex, Mongoose, raw driver |
| Java/Kotlin | JPA/Hibernate (`@Entity`, `spring-boot-starter-data-jpa`), Spring Data JDBC, jOOQ, MyBatis (`*Mapper.xml`), plain JDBC/`JdbcTemplate`, Exposed (Kotlin) |
| Python | SQLAlchemy (sync vs async: `AsyncSession`), SQLModel, Django ORM, Tortoise, Peewee, raw `psycopg`/`asyncpg` |
| Go | `database/sql`, pgx, sqlx, sqlc (`sqlc.yaml`), GORM, ent, Bun |
| .NET | Entity Framework Core (`DbContext`), Dapper, ADO.NET |
| Rust | SQLx, Diesel (`diesel.toml`), SeaORM |
| PHP / Ruby | Eloquent, Doctrine / ActiveRecord, Sequel |

**Migration tooling:** Flyway (`db/migration/V*__*.sql`), Liquibase (`changelog`), Alembic (`alembic.ini`, `versions/`), Django migrations, Prisma Migrate (`prisma/migrations`), Drizzle Kit, Knex, TypeORM migrations, EF Core `Migrations/`, golang-migrate, goose, Atlas, sqlx/diesel migrations, Rails `db/migrate`. Use the existing tool. Never add a second one.

## Test, build, and tooling signals

- **Test frameworks:** Jest, Vitest, Mocha, Playwright, Cypress, Testing Library; JUnit 4 vs 5 (`org.junit.jupiter`), TestNG, Mockito, MockK, AssertJ, Testcontainers, Spock, Kotest; pytest (`conftest.py`, `[tool.pytest.ini_options]`), unittest, Hypothesis; Go `testing`, testify, gomock; xUnit, NUnit, MSTest, FluentAssertions, Moq, NSubstitute; Rust `#[test]`, `cargo nextest`; PHPUnit, Pest; RSpec, Minitest.
- **Commands:** package.json `scripts`, `Makefile`, `justfile`, `Taskfile.yml`, `tox.ini`, `noxfile.py`, Gradle/Maven tasks, `.github/workflows/*`, `.gitlab-ci.yml`, `azure-pipelines.yml`, `Jenkinsfile`, `.circleci/config.yml`. CI shows which commands actually gate merges.
- **Lint/format/type:** ESLint/Biome/Prettier, `tsc --noEmit`; Checkstyle/Spotless/ktlint/detekt; Ruff/Black/isort/mypy/pyright; `gofmt`/`go vet`/golangci-lint; `dotnet format`, analyzers; `cargo fmt`/`clippy`; `.editorconfig`.
- **Code generation:** OpenAPI generators, protobuf/gRPC (`*.proto`, `buf.yaml`), GraphQL codegen, sqlc, Prisma client. Edit the source definition, then regenerate. Don't hand-edit the output.

## Monorepos and polyglot repositories

Signals: `pnpm-workspace.yaml`, `workspaces` in package.json, `nx.json`, `turbo.json`, `lerna.json`, Gradle multi-project `settings.gradle`, Maven `<modules>`, `go.work`, Cargo `[workspace]`, `.sln` with many projects, Bazel (`WORKSPACE`, `MODULE.bazel`, `BUILD`), Pants, or several unrelated manifests in sibling directories.

- Build the stack profile for the **package or service being changed**. Read its own manifest, then the shared root config (TS base config, Gradle conventions plugin, shared lint config).
- Packages in the same repo can use different frameworks, test runners, or even languages. Don't carry conventions across a package boundary without checking.
- Use the workspace's own commands for filtered runs (for example a workspace filter, a Gradle project path, or a Go package path) instead of running everything.
- Check for internal shared packages (UI kits, API clients, utilities) before writing a new one.

## Conflicting or weak evidence

- Manifest says X, code imports Y → trust the code that runs. Note the leftover dependency, but don't remove it as part of an unrelated task.
- Two libraries for the same job (two ORMs, two test runners) → find out which one recent code uses (check git history if available, or the most recently modified files), and follow that one. Mention the split.
- A migration in progress (old and new patterns side by side) → write new code in the new pattern, and only if the migration is clearly intentional and progressing. Otherwise follow the dominant pattern.
- Not enough evidence → say so in the stack profile's "Unknowns". Ask the user only if the answer changes the implementation materially and the codebase can't answer it.

## Version awareness

Read the installed versions from the lockfile or build file. Major versions change idioms. Apply the APIs of the installed version, and check the project's own code for confirmation before using a newer API. If documentation tooling is available in the environment, look up version-specific docs instead of relying on memory.
