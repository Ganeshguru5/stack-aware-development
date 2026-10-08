#!/usr/bin/env python3
"""Collect technology-stack signals from a repository.

Read-only and standard library only (Python 3.9+). Prints evidence about
languages, package managers, frameworks, databases, data-access layers,
migrations, test tools, and verification commands, grouped by project
(each directory with a manifest). Output is evidence for the agent to
confirm against source code -- not a verdict.

Usage:
    python detect_stack.py [ROOT] [--json] [--max-depth N]

Privacy: never reads real .env files; from example env files and app
config it reports only connection-URL schemes, never values.
"""
from __future__ import annotations

import argparse
import fnmatch
import glob
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

# Deep enough for typical monorepos (apps/<group>/<service>/...) while
# keeping the walk fast on very large repositories.
DEFAULT_MAX_DEPTH = 6
MAX_FILES = 60000
MAX_READ_BYTES = 1_000_000
# Unrecognized dependencies are listed so the agent can judge them itself;
# beyond this many the Markdown output summarizes (JSON always has all).
UNRECOGNIZED_SHOWN = 25

# Dependency/build output and tool directories. Every dot-directory is also
# skipped (.git, .venv, .next, .claude, .agents, .cursor, ...), as is any
# directory containing a SKILL.md (installed agent skills are not project code).
IGNORED_DIRS = {
    "node_modules", "vendor", "venv", "env", "target", "build", "dist", "out",
    "bin", "obj", "__pycache__", "site-packages", "coverage", "Pods",
    "DerivedData", "bower_components", "jspm_packages", "tmp", "temp", "logs",
}

MANIFESTS = {
    "package.json": "js", "pom.xml": "jvm", "build.gradle": "jvm",
    "build.gradle.kts": "jvm", "pyproject.toml": "python", "setup.py": "python",
    "setup.cfg": "python", "Pipfile": "python", "go.mod": "go",
    "Cargo.toml": "rust", "composer.json": "php", "Gemfile": "ruby",
    "mix.exs": "elixir", "pubspec.yaml": "dart", "Package.swift": "swift",
    "build.sbt": "scala", "deno.json": "js", "deno.jsonc": "js",
    "deps.edn": "clojure", "project.clj": "clojure",
}
MANIFEST_GLOBS = {"*.csproj": "dotnet", "*.fsproj": "dotnet", "*.vbproj": "dotnet",
                  "requirements*.txt": "python"}

LANG_NAMES = {
    "js": "JavaScript/TypeScript", "jvm": "Java/Kotlin (JVM)", "python": "Python",
    "go": "Go", "rust": "Rust", "dotnet": ".NET", "php": "PHP", "ruby": "Ruby",
    "elixir": "Elixir", "dart": "Dart", "swift": "Swift", "scala": "Scala",
    "clojure": "Clojure",
}

LOCKFILES = [
    ("pnpm-lock.yaml", "pnpm"), ("yarn.lock", "Yarn"), ("package-lock.json", "npm"),
    ("bun.lock", "Bun"), ("bun.lockb", "Bun"), ("deno.lock", "Deno"),
    ("uv.lock", "uv"), ("poetry.lock", "Poetry"), ("Pipfile.lock", "Pipenv"),
    ("pdm.lock", "PDM"), ("go.sum", "Go modules"), ("Cargo.lock", "Cargo"),
    ("composer.lock", "Composer"), ("Gemfile.lock", "Bundler"),
    ("packages.lock.json", "NuGet lock"), ("gradle.lockfile", "Gradle lock"),
    ("mix.lock", "Mix"), ("pubspec.lock", "pub"),
]

EXT_LANG = {
    ".ts": "TypeScript", ".tsx": "TypeScript", ".mts": "TypeScript", ".cts": "TypeScript",
    ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".java": "Java", ".kt": "Kotlin", ".kts": "Kotlin", ".scala": "Scala",
    ".groovy": "Groovy", ".clj": "Clojure", ".cljs": "ClojureScript", ".cljc": "Clojure", ".py": "Python", ".go": "Go", ".rs": "Rust", ".cs": "C#",
    ".fs": "F#", ".vb": "VB.NET", ".php": "PHP", ".rb": "Ruby", ".ex": "Elixir",
    ".exs": "Elixir", ".dart": "Dart", ".swift": "Swift", ".c": "C", ".h": "C/C++",
    ".cpp": "C++", ".cc": "C++", ".hpp": "C++", ".vue": "Vue", ".svelte": "Svelte",
    ".razor": "Razor", ".sql": "SQL",
}

# (ecosystem, category, label, patterns). Patterns are fnmatch globs matched
# against lowercase dependency identifiers. JVM identifiers are
# "group:artifact" plus "plugin:<id>"; .NET adds "sdk:<sdk>".
RULES = [
    # ---------------- JavaScript / TypeScript ----------------
    ("js", "framework", "Next.js", ["next"]),
    ("js", "framework", "React", ["react"]),
    ("js", "framework", "Vue", ["vue"]),
    ("js", "framework", "Nuxt", ["nuxt"]),
    ("js", "framework", "Angular", ["@angular/core"]),
    ("js", "framework", "Svelte", ["svelte"]),
    ("js", "framework", "SvelteKit", ["@sveltejs/kit"]),
    ("js", "framework", "Remix / React Router", ["@remix-run/*", "react-router", "@react-router/*"]),
    ("js", "framework", "Astro", ["astro"]),
    ("js", "framework", "Solid", ["solid-js"]),
    ("js", "framework", "React Native", ["react-native"]),
    ("js", "framework", "Expo", ["expo"]),
    ("js", "framework", "Electron", ["electron"]),
    ("js", "framework", "Express", ["express"]),
    ("js", "framework", "Fastify", ["fastify"]),
    ("js", "framework", "NestJS", ["@nestjs/core"]),
    ("js", "framework", "Koa", ["koa"]),
    ("js", "framework", "Hono", ["hono"]),
    ("js", "framework", "tRPC", ["@trpc/server"]),
    ("js", "framework", "GraphQL server", ["@apollo/server", "apollo-server*", "graphql-yoga", "mercurius"]),
    ("js", "database", "PostgreSQL", ["pg", "postgres", "@neondatabase/serverless", "@vercel/postgres"]),
    ("js", "database", "MySQL", ["mysql", "mysql2", "@planetscale/database"]),
    ("js", "database", "MariaDB", ["mariadb"]),
    ("js", "database", "SQLite", ["sqlite3", "better-sqlite3", "@libsql/client"]),
    ("js", "database", "MongoDB", ["mongodb"]),
    ("js", "database", "Redis", ["redis", "ioredis", "@upstash/redis"]),
    ("js", "database", "SQL Server", ["mssql", "tedious"]),
    ("js", "database", "Oracle", ["oracledb"]),
    ("js", "data_access", "Prisma", ["prisma", "@prisma/client"]),
    ("js", "data_access", "Drizzle", ["drizzle-orm"]),
    ("js", "data_access", "TypeORM", ["typeorm", "@nestjs/typeorm"]),
    ("js", "data_access", "Sequelize", ["sequelize", "sequelize-typescript"]),
    ("js", "data_access", "MikroORM", ["@mikro-orm/core"]),
    ("js", "data_access", "Kysely", ["kysely"]),
    ("js", "data_access", "Knex", ["knex"]),
    ("js", "data_access", "Mongoose", ["mongoose", "@nestjs/mongoose"]),
    ("js", "data_access", "Objection", ["objection"]),
    ("js", "testing", "Jest", ["jest", "ts-jest"]),
    ("js", "testing", "Vitest", ["vitest"]),
    ("js", "testing", "Mocha", ["mocha"]),
    ("js", "testing", "Playwright", ["@playwright/test", "playwright"]),
    ("js", "testing", "Cypress", ["cypress"]),
    ("js", "testing", "Testing Library", ["@testing-library/*"]),
    ("js", "testing", "Supertest", ["supertest"]),
    ("js", "testing", "MSW", ["msw"]),
    ("js", "testing", "nock", ["nock"]),
    ("js", "validation", "Zod", ["zod"]),
    ("js", "validation", "Yup", ["yup"]),
    ("js", "validation", "Joi", ["joi"]),
    ("js", "validation", "Valibot", ["valibot"]),
    ("js", "validation", "class-validator", ["class-validator"]),
    ("js", "validation", "Ajv / JSON Schema", ["ajv"]),
    ("js", "validation", "TypeBox", ["@sinclair/typebox"]),
    ("js", "auth", "Auth.js / NextAuth", ["next-auth", "@auth/*"]),
    ("js", "auth", "Better Auth", ["better-auth"]),
    ("js", "auth", "Passport", ["passport", "@nestjs/passport"]),
    ("js", "auth", "Clerk", ["@clerk/*"]),
    ("js", "auth", "Lucia", ["lucia"]),
    ("js", "auth", "Supabase", ["@supabase/supabase-js", "@supabase/ssr"]),
    ("js", "auth", "Firebase", ["firebase", "firebase-admin"]),
    ("js", "auth", "JWT library", ["jsonwebtoken", "jose", "@nestjs/jwt"]),
    ("js", "auth", "Sessions", ["express-session", "iron-session", "cookie-session", "@fastify/session"]),
    ("js", "state", "TanStack Query", ["@tanstack/react-query", "@tanstack/vue-query"]),
    ("js", "state", "SWR", ["swr"]),
    ("js", "state", "Redux", ["redux", "@reduxjs/toolkit"]),
    ("js", "state", "Zustand", ["zustand"]),
    ("js", "state", "Jotai", ["jotai"]),
    ("js", "state", "MobX", ["mobx"]),
    ("js", "state", "Pinia", ["pinia"]),
    ("js", "logging", "pino", ["pino"]),
    ("js", "logging", "winston", ["winston"]),
    ("js", "tooling", "TypeScript", ["typescript"]),
    ("js", "tooling", "ESLint", ["eslint"]),
    ("js", "tooling", "Biome", ["@biomejs/biome"]),
    ("js", "tooling", "Prettier", ["prettier"]),
    # ---------------- JVM ----------------
    ("jvm", "framework", "Spring Boot", ["org.springframework.boot:*", "plugin:org.springframework.boot"]),
    ("jvm", "framework", "Spring MVC (servlet)", ["*:spring-boot-starter-web", "org.springframework:spring-webmvc"]),
    ("jvm", "framework", "Spring WebFlux (reactive)", ["*:spring-boot-starter-webflux", "org.springframework:spring-webflux"]),
    ("jvm", "framework", "Quarkus", ["io.quarkus:*", "plugin:io.quarkus"]),
    ("jvm", "framework", "Micronaut", ["io.micronaut*:*", "plugin:io.micronaut.*"]),
    ("jvm", "framework", "Jakarta EE", ["jakarta.platform:*"]),
    ("jvm", "framework", "Ktor", ["io.ktor:*", "plugin:io.ktor.plugin"]),
    ("jvm", "framework", "Dropwizard", ["io.dropwizard:*"]),
    ("jvm", "framework", "Vert.x", ["io.vertx:*"]),
    ("jvm", "database", "PostgreSQL", ["org.postgresql:*"]),
    ("jvm", "database", "MySQL", ["com.mysql:*", "mysql:mysql-connector-java"]),
    ("jvm", "database", "MariaDB", ["org.mariadb.jdbc:*"]),
    ("jvm", "database", "SQLite", ["org.xerial:sqlite-jdbc"]),
    ("jvm", "database", "SQL Server", ["com.microsoft.sqlserver:*"]),
    ("jvm", "database", "Oracle", ["com.oracle.database.jdbc:*"]),
    ("jvm", "database", "H2 (often tests only)", ["com.h2database:h2"]),
    ("jvm", "database", "MongoDB", ["org.mongodb:*", "*:spring-boot-starter-data-mongodb*"]),
    ("jvm", "database", "Redis", ["*:spring-boot-starter-data-redis*", "redis.clients:jedis", "io.lettuce:*"]),
    ("jvm", "data_access", "JPA / Hibernate", ["*:spring-boot-starter-data-jpa", "org.hibernate.orm:*", "org.hibernate:hibernate-core", "jakarta.persistence:*", "io.quarkus:quarkus-hibernate-orm*"]),
    ("jvm", "data_access", "Spring Data JDBC", ["*:spring-boot-starter-data-jdbc"]),
    ("jvm", "data_access", "JDBC / JdbcTemplate", ["*:spring-boot-starter-jdbc", "org.springframework:spring-jdbc"]),
    ("jvm", "data_access", "R2DBC", ["*:spring-boot-starter-data-r2dbc", "io.r2dbc:*"]),
    ("jvm", "data_access", "jOOQ", ["org.jooq:*", "*:spring-boot-starter-jooq"]),
    ("jvm", "data_access", "MyBatis", ["org.mybatis*:*"]),
    ("jvm", "data_access", "Exposed", ["org.jetbrains.exposed:*"]),
    ("jvm", "migrations", "Flyway", ["org.flywaydb:*", "plugin:org.flywaydb.flyway"]),
    ("jvm", "migrations", "Liquibase", ["org.liquibase:*", "plugin:org.liquibase.gradle"]),
    ("jvm", "testing", "JUnit 5", ["org.junit.jupiter:*", "org.junit:junit-bom"]),
    ("jvm", "testing", "JUnit 4", ["junit:junit"]),
    ("jvm", "testing", "Spring Boot Test", ["*:spring-boot-starter-test"]),
    ("jvm", "testing", "Mockito", ["org.mockito:*"]),
    ("jvm", "testing", "MockK", ["io.mockk:*"]),
    ("jvm", "testing", "AssertJ", ["org.assertj:*"]),
    ("jvm", "testing", "Testcontainers", ["org.testcontainers:*"]),
    ("jvm", "testing", "Spock", ["org.spockframework:*"]),
    ("jvm", "testing", "Kotest", ["io.kotest:*"]),
    ("jvm", "testing", "TestNG", ["org.testng:*"]),
    ("jvm", "testing", "REST Assured", ["io.rest-assured:*"]),
    ("jvm", "validation", "Bean Validation", ["*:spring-boot-starter-validation", "jakarta.validation:*", "javax.validation:*", "org.hibernate.validator:*"]),
    ("jvm", "auth", "Spring Security", ["*:spring-boot-starter-security", "org.springframework.security:*"]),
    ("jvm", "auth", "OAuth2 / OIDC", ["*:spring-boot-starter-oauth2-*"]),
    ("jvm", "auth", "JWT library", ["io.jsonwebtoken:*", "com.auth0:java-jwt", "com.nimbusds:*"]),
    ("jvm", "other", "Lombok", ["org.projectlombok:*", "plugin:io.freefair.lombok"]),
    ("jvm", "other", "MapStruct", ["org.mapstruct:*"]),
    ("jvm", "other", "Kotlin", ["org.jetbrains.kotlin:*", "plugin:org.jetbrains.kotlin.*", "plugin:kotlin"]),
    # ---------------- Python ----------------
    ("python", "framework", "FastAPI", ["fastapi"]),
    ("python", "framework", "Django", ["django"]),
    ("python", "framework", "Django REST Framework", ["djangorestframework"]),
    ("python", "framework", "Flask", ["flask"]),
    ("python", "framework", "Litestar", ["litestar"]),
    ("python", "framework", "Starlette", ["starlette"]),
    ("python", "framework", "aiohttp", ["aiohttp"]),
    ("python", "framework", "Tornado", ["tornado"]),
    ("python", "framework", "Sanic", ["sanic"]),
    ("python", "framework", "Quart", ["quart"]),
    ("python", "database", "PostgreSQL", ["psycopg", "psycopg2", "psycopg2-binary", "psycopg-binary", "asyncpg", "pg8000"]),
    ("python", "database", "MySQL", ["mysqlclient", "pymysql", "mysql-connector-python", "aiomysql", "asyncmy"]),
    ("python", "database", "SQLite", ["aiosqlite"]),
    ("python", "database", "MongoDB", ["pymongo", "motor"]),
    ("python", "database", "Redis", ["redis", "aioredis"]),
    ("python", "database", "SQL Server", ["pyodbc", "pymssql", "aioodbc"]),
    ("python", "database", "Oracle", ["oracledb", "cx-oracle"]),
    ("python", "data_access", "SQLAlchemy", ["sqlalchemy", "flask-sqlalchemy"]),
    ("python", "data_access", "SQLModel", ["sqlmodel"]),
    ("python", "data_access", "Django ORM", ["django"]),
    ("python", "data_access", "Tortoise ORM", ["tortoise-orm"]),
    ("python", "data_access", "Peewee", ["peewee"]),
    ("python", "data_access", "MongoDB ODM", ["beanie", "mongoengine", "odmantic"]),
    ("python", "migrations", "Alembic", ["alembic", "flask-migrate"]),
    ("python", "testing", "pytest", ["pytest"]),
    ("python", "testing", "pytest-asyncio / anyio", ["pytest-asyncio", "anyio"]),
    ("python", "testing", "pytest-django", ["pytest-django"]),
    ("python", "testing", "Hypothesis", ["hypothesis"]),
    ("python", "testing", "factories", ["factory-boy", "model-bakery"]),
    ("python", "testing", "HTTP mocking", ["responses", "respx", "pytest-httpx"]),
    ("python", "testing", "tox / nox", ["tox", "nox"]),
    ("python", "validation", "Pydantic", ["pydantic", "pydantic-settings"]),
    ("python", "validation", "marshmallow", ["marshmallow"]),
    ("python", "auth", "JWT library", ["pyjwt", "python-jose", "authlib"]),
    ("python", "auth", "Password hashing", ["passlib", "bcrypt", "argon2-cffi", "pwdlib"]),
    ("python", "auth", "Framework auth add-on", ["fastapi-users", "django-allauth", "flask-login", "djangorestframework-simplejwt", "dj-rest-auth"]),
    ("python", "other", "Celery", ["celery"]),
    ("python", "tooling", "Ruff", ["ruff"]),
    ("python", "tooling", "Black", ["black"]),
    ("python", "tooling", "mypy", ["mypy"]),
    ("python", "tooling", "Pyright", ["pyright"]),
    # ---------------- Go ----------------
    ("go", "framework", "Gin", ["github.com/gin-gonic/gin"]),
    ("go", "framework", "Echo", ["github.com/labstack/echo*"]),
    ("go", "framework", "Fiber", ["github.com/gofiber/fiber*"]),
    ("go", "framework", "Chi", ["github.com/go-chi/chi*"]),
    ("go", "framework", "gorilla/mux", ["github.com/gorilla/mux"]),
    ("go", "framework", "gRPC", ["google.golang.org/grpc"]),
    ("go", "framework", "gqlgen (GraphQL)", ["github.com/99designs/gqlgen"]),
    ("go", "database", "PostgreSQL", ["github.com/jackc/pgx*", "github.com/lib/pq"]),
    ("go", "database", "MySQL", ["github.com/go-sql-driver/mysql"]),
    ("go", "database", "SQLite", ["github.com/mattn/go-sqlite3", "modernc.org/sqlite", "github.com/glebarez/sqlite"]),
    ("go", "database", "MongoDB", ["go.mongodb.org/mongo-driver*"]),
    ("go", "database", "Redis", ["github.com/redis/go-redis*", "github.com/go-redis/redis*", "github.com/gomodule/redigo"]),
    ("go", "database", "SQL Server", ["github.com/microsoft/go-mssqldb", "github.com/denisenkom/go-mssqldb"]),
    ("go", "data_access", "pgx", ["github.com/jackc/pgx*"]),
    ("go", "data_access", "sqlx", ["github.com/jmoiron/sqlx"]),
    ("go", "data_access", "GORM", ["gorm.io/gorm"]),
    ("go", "data_access", "ent", ["entgo.io/ent"]),
    ("go", "data_access", "Bun", ["github.com/uptrace/bun"]),
    ("go", "data_access", "query builder", ["github.com/masterminds/squirrel", "github.com/doug-martin/goqu*"]),
    ("go", "migrations", "golang-migrate", ["github.com/golang-migrate/migrate*"]),
    ("go", "migrations", "goose", ["github.com/pressly/goose*"]),
    ("go", "migrations", "Atlas", ["ariga.io/atlas*"]),
    ("go", "testing", "testify", ["github.com/stretchr/testify"]),
    ("go", "testing", "gomock", ["github.com/golang/mock", "go.uber.org/mock"]),
    ("go", "testing", "Ginkgo/Gomega", ["github.com/onsi/ginkgo*", "github.com/onsi/gomega"]),
    ("go", "testing", "Testcontainers", ["github.com/testcontainers/testcontainers-go*"]),
    ("go", "validation", "go-playground/validator", ["github.com/go-playground/validator*"]),
    ("go", "validation", "ozzo-validation", ["github.com/go-ozzo/ozzo-validation*"]),
    ("go", "auth", "JWT library", ["github.com/golang-jwt/jwt*", "github.com/lestrrat-go/jwx*"]),
    ("go", "auth", "OAuth2 / OIDC", ["golang.org/x/oauth2", "github.com/coreos/go-oidc*"]),
    ("go", "logging", "zap", ["go.uber.org/zap"]),
    ("go", "logging", "zerolog", ["github.com/rs/zerolog"]),
    ("go", "logging", "logrus", ["github.com/sirupsen/logrus"]),
    ("go", "other", "DI (wire/fx)", ["github.com/google/wire", "go.uber.org/fx"]),
    # ---------------- Rust ----------------
    ("rust", "framework", "Axum", ["axum"]),
    ("rust", "framework", "Actix Web", ["actix-web"]),
    ("rust", "framework", "Rocket", ["rocket"]),
    ("rust", "framework", "Warp", ["warp"]),
    ("rust", "framework", "Poem", ["poem"]),
    ("rust", "framework", "Tonic (gRPC)", ["tonic"]),
    ("rust", "database", "PostgreSQL", ["tokio-postgres", "postgres"]),
    ("rust", "database", "MySQL", ["mysql", "mysql_async"]),
    ("rust", "database", "SQLite", ["rusqlite"]),
    ("rust", "database", "MongoDB", ["mongodb"]),
    ("rust", "database", "Redis", ["redis", "fred"]),
    ("rust", "data_access", "SQLx", ["sqlx"]),
    ("rust", "data_access", "Diesel", ["diesel"]),
    ("rust", "data_access", "SeaORM", ["sea-orm"]),
    ("rust", "testing", "mockall", ["mockall"]),
    ("rust", "testing", "rstest", ["rstest"]),
    ("rust", "testing", "proptest", ["proptest"]),
    ("rust", "testing", "insta", ["insta"]),
    ("rust", "validation", "validator / garde", ["validator", "garde"]),
    ("rust", "other", "Tokio runtime", ["tokio"]),
    ("rust", "other", "Error crates", ["thiserror", "anyhow", "eyre", "color-eyre"]),
    # ---------------- .NET ----------------
    ("dotnet", "framework", "ASP.NET Core", ["sdk:microsoft.net.sdk.web", "microsoft.aspnetcore.app"]),
    ("dotnet", "framework", "Blazor", ["sdk:microsoft.net.sdk.blazorwebassembly", "microsoft.aspnetcore.components.webassembly*"]),
    ("dotnet", "framework", "gRPC", ["grpc.aspnetcore*"]),
    ("dotnet", "framework", "GraphQL (Hot Chocolate)", ["hotchocolate*"]),
    ("dotnet", "framework", "Worker service", ["sdk:microsoft.net.sdk.worker"]),
    ("dotnet", "database", "PostgreSQL", ["npgsql*"]),
    ("dotnet", "database", "MySQL", ["mysqlconnector", "mysql.data", "pomelo.entityframeworkcore.mysql"]),
    ("dotnet", "database", "SQLite", ["microsoft.data.sqlite*", "microsoft.entityframeworkcore.sqlite*"]),
    ("dotnet", "database", "SQL Server", ["microsoft.data.sqlclient", "system.data.sqlclient", "microsoft.entityframeworkcore.sqlserver"]),
    ("dotnet", "database", "MongoDB", ["mongodb.driver"]),
    ("dotnet", "database", "Redis", ["stackexchange.redis", "microsoft.extensions.caching.stackexchangeredis"]),
    ("dotnet", "database", "Oracle", ["oracle.*"]),
    ("dotnet", "data_access", "Entity Framework Core", ["microsoft.entityframeworkcore*"]),
    ("dotnet", "data_access", "Dapper", ["dapper"]),
    ("dotnet", "testing", "xUnit", ["xunit*"]),
    ("dotnet", "testing", "NUnit", ["nunit*"]),
    ("dotnet", "testing", "MSTest", ["mstest*"]),
    ("dotnet", "testing", "Moq", ["moq"]),
    ("dotnet", "testing", "NSubstitute", ["nsubstitute"]),
    ("dotnet", "testing", "FluentAssertions / Shouldly", ["fluentassertions", "shouldly"]),
    ("dotnet", "testing", "WebApplicationFactory", ["microsoft.aspnetcore.mvc.testing"]),
    ("dotnet", "testing", "Testcontainers", ["testcontainers*"]),
    ("dotnet", "testing", "bUnit", ["bunit*"]),
    ("dotnet", "validation", "FluentValidation", ["fluentvalidation*"]),
    ("dotnet", "auth", "ASP.NET Core auth", ["microsoft.aspnetcore.authentication*", "microsoft.aspnetcore.identity*", "microsoft.identity.web*"]),
    ("dotnet", "logging", "Serilog", ["serilog*"]),
    ("dotnet", "other", "MediatR", ["mediatr*"]),
    ("dotnet", "other", "Object mapping", ["automapper*", "mapster*"]),
    # ---------------- PHP ----------------
    ("php", "framework", "Laravel", ["laravel/framework"]),
    ("php", "framework", "Symfony", ["symfony/framework-bundle"]),
    ("php", "framework", "Slim", ["slim/slim"]),
    ("php", "data_access", "Doctrine ORM", ["doctrine/orm"]),
    ("php", "data_access", "Eloquent", ["illuminate/database", "laravel/framework"]),
    ("php", "database", "Redis", ["predis/predis"]),
    ("php", "database", "MongoDB", ["mongodb/mongodb", "mongodb/laravel-mongodb"]),
    ("php", "migrations", "Doctrine Migrations", ["doctrine/doctrine-migrations-bundle", "doctrine/migrations"]),
    ("php", "testing", "PHPUnit", ["phpunit/phpunit"]),
    ("php", "testing", "Pest", ["pestphp/pest"]),
    ("php", "tooling", "PHPStan / Psalm", ["phpstan/phpstan", "vimeo/psalm", "larastan/larastan"]),
    # ---------------- Ruby ----------------
    ("ruby", "framework", "Rails", ["rails"]),
    ("ruby", "framework", "Sinatra", ["sinatra"]),
    ("ruby", "framework", "Hanami", ["hanami"]),
    ("ruby", "database", "PostgreSQL", ["pg"]),
    ("ruby", "database", "MySQL", ["mysql2", "trilogy"]),
    ("ruby", "database", "SQLite", ["sqlite3"]),
    ("ruby", "database", "MongoDB", ["mongoid", "mongo"]),
    ("ruby", "database", "Redis", ["redis"]),
    ("ruby", "data_access", "ActiveRecord", ["rails", "activerecord"]),
    ("ruby", "data_access", "Sequel", ["sequel"]),
    ("ruby", "testing", "RSpec", ["rspec", "rspec-rails"]),
    ("ruby", "testing", "Minitest", ["minitest"]),
    ("ruby", "testing", "factory_bot", ["factory_bot*"]),
    ("ruby", "testing", "Capybara", ["capybara"]),
    ("ruby", "auth", "Devise", ["devise"]),
    ("ruby", "auth", "Authorization (Pundit/CanCanCan)", ["pundit", "cancancan"]),
    ("ruby", "tooling", "RuboCop", ["rubocop*"]),
]

# File/directory markers relative to a project directory.
FILE_MARKERS = [
    ("tsconfig.json", "tooling", "TypeScript config"),
    ("next.config.js", "framework", "Next.js config"),
    ("next.config.mjs", "framework", "Next.js config"),
    ("next.config.ts", "framework", "Next.js config"),
    ("nuxt.config.ts", "framework", "Nuxt config"),
    ("angular.json", "framework", "Angular workspace"),
    ("nest-cli.json", "framework", "NestJS CLI config"),
    ("svelte.config.js", "framework", "Svelte config"),
    ("vite.config.ts", "tooling", "Vite config"),
    ("vite.config.js", "tooling", "Vite config"),
    ("drizzle.config.ts", "data_access", "Drizzle config"),
    ("drizzle.config.js", "data_access", "Drizzle config"),
    ("prisma/migrations", "migrations", "Prisma Migrate"),
    ("jest.config.js", "testing", "Jest config"),
    ("jest.config.ts", "testing", "Jest config"),
    ("vitest.config.ts", "testing", "Vitest config"),
    ("vitest.config.mts", "testing", "Vitest config"),
    ("playwright.config.ts", "testing", "Playwright config"),
    ("cypress.config.ts", "testing", "Cypress config"),
    ("manage.py", "framework", "Django manage.py"),
    ("alembic.ini", "migrations", "Alembic"),
    ("conftest.py", "testing", "pytest conftest"),
    ("pytest.ini", "testing", "pytest config"),
    ("tox.ini", "testing", "tox"),
    ("noxfile.py", "testing", "nox"),
    ("mvnw", "tooling", "Maven wrapper"),
    ("gradlew", "tooling", "Gradle wrapper"),
    ("gradle/libs.versions.toml", "tooling", "Gradle version catalog"),
    ("src/main/kotlin", "other", "Kotlin sources"),
    ("src/main/resources/db/migration", "migrations", "Flyway-style migrations"),
    ("src/main/resources/db/changelog", "migrations", "Liquibase changelog"),
    ("sqlc.yaml", "data_access", "sqlc"),
    ("sqlc.yml", "data_access", "sqlc"),
    ("sqlc.json", "data_access", "sqlc"),
    ("diesel.toml", "data_access", "Diesel config"),
    ("Directory.Packages.props", "tooling", "NuGet central package management"),
    ("Directory.Build.props", "tooling", "MSBuild shared props"),
    ("global.json", "tooling", ".NET SDK pin"),
    ("Migrations", "migrations", "EF Core-style Migrations folder"),
    ("artisan", "framework", "Laravel artisan"),
    ("bin/console", "framework", "Symfony console"),
    ("config/application.rb", "framework", "Rails application"),
    ("db/migrate", "migrations", "Rails-style migrations"),
    ("migrations", "migrations", "migrations folder"),
    ("db/migrations", "migrations", "migrations folder"),
    ("buf.yaml", "tooling", "Buf (protobuf)"),
    ("openapi.yaml", "tooling", "OpenAPI spec"),
    ("openapi.json", "tooling", "OpenAPI spec"),
]

ROOT_MARKERS = [
    ("pnpm-workspace.yaml", "pnpm workspace"), ("nx.json", "Nx"), ("turbo.json", "Turborepo"),
    ("lerna.json", "Lerna"), ("rush.json", "Rush"), ("go.work", "Go workspace"),
    ("WORKSPACE", "Bazel"), ("WORKSPACE.bazel", "Bazel"), ("MODULE.bazel", "Bazel"),
    ("pants.toml", "Pants"),
]
CI_PATHS = [".github/workflows", ".gitlab-ci.yml", "Jenkinsfile", "azure-pipelines.yml",
            ".circleci/config.yml", "bitbucket-pipelines.yml", ".buildkite", ".drone.yml",
            ".travis.yml"]
CONVENTION_DOCS = ["AGENTS.md", "CLAUDE.md", "CONTRIBUTING.md", ".editorconfig",
                   "ARCHITECTURE.md", "docs/adr", "docs/decisions", ".github/copilot-instructions.md",
                   ".cursorrules"]
VERSION_PINS = [".nvmrc", ".node-version", ".python-version", ".tool-versions",
                ".java-version", ".sdkmanrc", "rust-toolchain", "rust-toolchain.toml",
                ".ruby-version", "mise.toml", ".mise.toml"]
ENV_EXAMPLES = [".env.example", ".env.sample", ".env.template", ".env.dist", "example.env"]

URL_SCHEMES = [
    (re.compile(r"\bpostgres(?:ql)?(?:\+\w+)?://", re.I), "PostgreSQL"),
    (re.compile(r"\bjdbc:postgresql:", re.I), "PostgreSQL"),
    (re.compile(r"\bmysql(?:\+\w+)?://|\bjdbc:mysql:", re.I), "MySQL"),
    (re.compile(r"\bmariadb://|\bjdbc:mariadb:", re.I), "MariaDB"),
    (re.compile(r"\bsqlite(?:\+\w+)?:|\bjdbc:sqlite:", re.I), "SQLite"),
    (re.compile(r"\bmongodb(?:\+srv)?://", re.I), "MongoDB"),
    (re.compile(r"\brediss?://", re.I), "Redis"),
    (re.compile(r"\bsqlserver://|\bmssql(?:\+\w+)?://|\bjdbc:sqlserver:", re.I), "SQL Server"),
    (re.compile(r"\bjdbc:oracle:|\boracle(?:\+\w+)?://", re.I), "Oracle"),
    (re.compile(r"\bjdbc:h2:", re.I), "H2"),
]
IMAGE_DB = [("postgres", "PostgreSQL"), ("postgis", "PostgreSQL"), ("mysql", "MySQL"),
            ("mariadb", "MariaDB"), ("mongo", "MongoDB"), ("redis", "Redis"),
            ("valkey", "Redis-compatible (Valkey)"), ("mssql", "SQL Server"),
            ("oracle", "Oracle"), ("elasticsearch", "Elasticsearch"),
            ("opensearch", "OpenSearch"), ("rabbitmq", "RabbitMQ"), ("kafka", "Kafka"),
            ("localstack", "LocalStack (AWS emulation)"), ("minio", "MinIO (S3-compatible)")]
DJANGO_ENGINES = {"postgresql": "PostgreSQL", "mysql": "MySQL", "sqlite3": "SQLite",
                  "oracle": "Oracle"}
PRISMA_PROVIDERS = {"postgresql": "PostgreSQL", "postgres": "PostgreSQL", "mysql": "MySQL",
                    "sqlite": "SQLite", "sqlserver": "SQL Server", "mongodb": "MongoDB",
                    "cockroachdb": "CockroachDB"}


def read_text(path):
    try:
        with open(path, "rb") as fh:
            data = fh.read(MAX_READ_BYTES)
        return data.decode("utf-8", errors="replace")
    except OSError:
        return ""


def rel(root, path):
    r = os.path.relpath(path, root).replace(os.sep, "/")
    return "." if r == "." else r


def exists_exact(base, relpath):
    """Case-sensitive existence check, also on case-insensitive filesystems
    (so 'migrations/' is not mistaken for an EF Core 'Migrations/' folder)."""
    current = base
    for part in relpath.split("/"):
        try:
            if part not in os.listdir(current):
                return False
        except OSError:
            return False
        current = os.path.join(current, part)
    return True


def norm_py(name):
    return re.sub(r"[-_.]+", "-", name).lower()


# ---------------------------------------------------------------- parsers
def deps_package_json(path, info):
    try:
        data = json.loads(read_text(path) or "{}")
    except ValueError:
        info["notes"].append("package.json could not be parsed")
        return {}
    deps = {}
    for key in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        for name, ver in (data.get(key) or {}).items():
            deps[name.lower()] = str(ver)
    if data.get("packageManager"):
        info["package_managers"].append("{} (packageManager field)".format(data["packageManager"]))
    if data.get("type") == "module":
        info["notes"].append('"type": "module" (ESM)')
    if data.get("workspaces"):
        info["notes"].append("declares workspaces (monorepo root)")
    engines = data.get("engines") or {}
    if engines.get("node"):
        info["versions"].append("node {} (engines)".format(engines["node"]))
    scripts = data.get("scripts") or {}
    for name in ("test", "test:unit", "test:e2e", "lint", "typecheck", "type-check",
                 "check", "build", "format", "e2e"):
        if name in scripts:
            info["commands"].append("script {}: {}".format(name, str(scripts[name])[:80]))
    return deps


def _strip_ns(tag):
    return tag.rsplit("}", 1)[-1]


def deps_pom(path, info):
    deps = {}
    try:
        tree = ET.fromstring(read_text(path))
    except ET.ParseError:
        info["notes"].append("pom.xml could not be parsed")
        return deps
    for el in tree.iter():
        tag = _strip_ns(el.tag)
        if tag in ("dependency", "plugin", "parent"):
            g = a = v = ""
            for child in el:
                ct = _strip_ns(child.tag)
                if ct == "groupId":
                    g = (child.text or "").strip()
                elif ct == "artifactId":
                    a = (child.text or "").strip()
                elif ct == "version":
                    v = (child.text or "").strip()
            if a:
                deps["{}:{}".format(g, a).lower()] = v
        elif tag in ("java.version", "maven.compiler.release", "maven.compiler.source"):
            info["versions"].append("java {} (pom {})".format((el.text or "").strip(), tag))
        elif tag == "module":
            info["notes"].append("Maven module: {}".format((el.text or "").strip()))
    return deps


GRADLE_COORD = re.compile(r"""["']([\w.\-]+):([\w.\-]+)(?::([^"'\s]+))?["']""")
GRADLE_PLUGIN = re.compile(r"""\bid\s*\(?\s*["']([\w.\-]+)["']""")
GRADLE_KOTLIN = re.compile(r"""\bkotlin\s*\(\s*["'](\w+)["']""")
TOML_PLUGIN = re.compile(r"""\bid\s*=\s*["']([\w.\-]+)["']""")
TOML_MODULE = re.compile(r"""\bgroup\s*=\s*["']([\w.\-]+)["']\s*,\s*name\s*=\s*["']([\w.\-]+)["']""")
GRADLE_JAVA = re.compile(r"JavaLanguageVersion\.of\(\s*(\d+)\s*\)|sourceCompatibility\s*=\s*['\"]?(?:JavaVersion\.VERSION_)?([\d._]+)")


def deps_gradle(path, info):
    text = read_text(path)
    deps = {}
    for g, a, v in GRADLE_COORD.findall(text):
        deps["{}:{}".format(g, a).lower()] = v or ""
    for pid in GRADLE_PLUGIN.findall(text):
        deps["plugin:" + pid.lower()] = ""
    for k in GRADLE_KOTLIN.findall(text):
        deps["plugin:kotlin"] = ""
        if k == "jvm":
            deps["plugin:org.jetbrains.kotlin.jvm"] = ""
    for m in GRADLE_JAVA.finditer(text):
        info["versions"].append("java {} ({})".format(m.group(1) or m.group(2), os.path.basename(path)))
    if os.path.basename(path).startswith("settings.gradle") and "include" in text:
        info["notes"].append("Gradle multi-project build (settings.gradle includes)")
    return deps


def deps_version_catalog(path):
    text = read_text(path)
    deps = {}
    for g, a, v in GRADLE_COORD.findall(text):
        deps["{}:{}".format(g, a).lower()] = v or ""
    for g, a in TOML_MODULE.findall(text):
        deps["{}:{}".format(g, a).lower()] = ""
    for pid in TOML_PLUGIN.findall(text):
        deps["plugin:" + pid.lower()] = ""
    return deps


REQ_LINE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._\-]*)\s*(\[[^\]]*\])?\s*([<>=!~^].*)?$")
PY_QUOTED_REQ = re.compile(r"""["']\s*([A-Za-z0-9][A-Za-z0-9._\-]*)\s*(?:\[[^\]]*\])?\s*([<>=!~^][^"';]*)?""")
TOML_KEY = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._\-]*)\s*=", re.M)


def deps_requirements(path, info):
    deps = {}
    for line in read_text(path).splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        m = REQ_LINE.match(line)
        if m:
            deps[norm_py(m.group(1))] = (m.group(3) or "").strip()
    return deps


QUOTED = re.compile(r""""[^"]*"|'[^']*'""")
ARRAY_START = re.compile(r"^([A-Za-z0-9_.\-]+)\s*=\s*\[(.*)$")


def _collect_quoted(fragment, deps):
    for name, ver in PY_QUOTED_REQ.findall(fragment):
        deps.setdefault(norm_py(name), (ver or "").strip())


def deps_pyproject(path, info):
    """Section-aware parse of pyproject.toml / Pipfile dependency declarations.

    Only dependency sections are read, so names in descriptions or tool
    config are not mistaken for dependencies.
    """
    text = read_text(path)
    deps = {}
    section, in_array = "", False
    for raw in text.splitlines():
        s = raw.strip()
        if s.startswith("#"):
            continue
        if in_array:
            _collect_quoted(s, deps)
            if "]" in QUOTED.sub("", s):
                in_array = False
            continue
        if s.startswith("["):
            section = s.strip("[] ").lower()
            continue
        dep_section = ("dependencies" in section or "dependency-groups" in section
                       or section in ("packages", "dev-packages"))
        m = ARRAY_START.match(s)
        if m and (dep_section or m.group(1) in ("dependencies", "dev-dependencies", "requires")):
            _collect_quoted(m.group(2), deps)
            in_array = "]" not in QUOTED.sub("", m.group(2))
            continue
        if dep_section:  # Poetry/PDM/Pipfile tables: name = "^1.2" or name = {...}
            k = TOML_KEY.match(s)
            if k and k.group(1).lower() != "python":
                deps.setdefault(norm_py(k.group(1)), "")
    for tool, label in (("[tool.poetry", "Poetry"), ("[tool.uv", "uv"), ("[tool.pdm", "PDM"),
                        ("[tool.hatch", "Hatch")):
        if tool in text:
            info["package_managers"].append("{} ([tool.*] section in pyproject.toml)".format(label))
    m = re.search(r"""requires-python\s*=\s*["']([^"']+)["']""", text)
    if m:
        info["versions"].append("python {} (requires-python)".format(m.group(1)))
    if "[tool.pytest" in text:
        info["markers"]["testing"].append("pytest config in pyproject.toml")
    for tool in ("ruff", "black", "mypy", "pyright", "isort"):
        if "[tool.{}".format(tool) in text:
            info["markers"]["tooling"].append("{} config in pyproject.toml".format(tool))
    return deps


def deps_gomod(path, info):
    text = read_text(path)
    deps = {}
    m = re.search(r"^go\s+(\S+)", text, re.M)
    if m:
        info["versions"].append("go {} (go.mod)".format(m.group(1)))
    m = re.search(r"^module\s+(\S+)", text, re.M)
    if m:
        info["notes"].append("module path: {}".format(m.group(1)))
    for mod, ver in re.findall(r"^\s*(?:require\s+)?([\w.\-]+\.[\w.\-]+/[\w.\-/]+)\s+(v[\w.\-+]+)", text, re.M):
        deps[mod.lower()] = ver
    return deps


def deps_cargo(path, info):
    text = read_text(path)
    deps = {}
    section = ""
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("["):
            section = s
            continue
        if "dependencies" in section:
            m = re.match(r"([A-Za-z0-9_\-]+)(?:\.workspace)?\s*=\s*(.*)", s)
            if m:
                ver = re.search(r"""["']([^"']+)["']""", m.group(2))
                deps[m.group(1).lower()] = ver.group(1) if ver else ""
    m = re.search(r"""^edition\s*=\s*["'](\d+)["']""", text, re.M)
    if m:
        info["versions"].append("Rust edition {}".format(m.group(1)))
    m = re.search(r"""^rust-version\s*=\s*["']([^"']+)["']""", text, re.M)
    if m:
        info["versions"].append("rust-version {} (MSRV)".format(m.group(1)))
    if "[workspace]" in text:
        info["notes"].append("Cargo workspace")
    return deps


def deps_csproj(path, info):
    text = read_text(path)
    deps = {}
    m = re.search(r"""<Project\s+Sdk\s*=\s*["']([^"']+)["']""", text)
    if m:
        deps["sdk:" + m.group(1).lower()] = ""
    for name, ver in re.findall(r"""<PackageReference\s+Include\s*=\s*["']([^"']+)["'](?:\s+Version\s*=\s*["']([^"']*)["'])?""", text):
        deps[name.lower()] = ver
    for tf in re.findall(r"<TargetFrameworks?>([^<]+)</TargetFrameworks?>", text):
        info["versions"].append("{} ({})".format(tf.strip(), os.path.basename(path)))
    if re.search(r"<Nullable>\s*enable\s*</Nullable>", text):
        info["notes"].append("nullable reference types enabled ({})".format(os.path.basename(path)))
    return deps


def deps_composer(path, info):
    try:
        data = json.loads(read_text(path) or "{}")
    except ValueError:
        return {}
    deps = {}
    for key in ("require", "require-dev"):
        for name, ver in (data.get(key) or {}).items():
            deps[name.lower()] = str(ver)
    if "php" in deps:
        info["versions"].append("php {} (composer.json)".format(deps["php"]))
    return deps


def deps_gemfile(path, info):
    deps = {}
    for name, rest in re.findall(r"""^\s*gem\s+["']([^"']+)["'](.*)$""", read_text(path), re.M):
        ver = re.search(r"""["']([^"']+)["']""", rest)
        deps[name.lower()] = ver.group(1) if ver else ""
    m = re.search(r"""^\s*ruby\s+["']([^"']+)["']""", read_text(path), re.M)
    if m:
        info["versions"].append("ruby {} (Gemfile)".format(m.group(1)))
    return deps


PARSERS = {
    "package.json": deps_package_json, "pom.xml": deps_pom, "build.gradle": deps_gradle,
    "build.gradle.kts": deps_gradle, "settings.gradle": deps_gradle,
    "settings.gradle.kts": deps_gradle, "pyproject.toml": deps_pyproject,
    "Pipfile": deps_pyproject, "setup.cfg": deps_requirements, "go.mod": deps_gomod,
    "Cargo.toml": deps_cargo, "composer.json": deps_composer, "Gemfile": deps_gemfile,
}


# ---------------------------------------------------------------- lockfiles
# Resolved versions matter more than declared ranges: idioms change between
# major versions. Each parser returns {dependency-id: resolved-version}.
TOML_PKG_BLOCK = re.compile(r'^\[\[package\]\]\s*\nname\s*=\s*"([^"]+)"\s*\nversion\s*=\s*"([^"]+)"', re.M)


def lock_toml_packages(path, normalize=lambda n: n.lower()):
    """poetry.lock, uv.lock, Cargo.lock: [[package]] name/version blocks."""
    return {normalize(n): v for n, v in TOML_PKG_BLOCK.findall(read_text(path))}


def lock_package_json(path, rel_dir):
    try:
        data = json.loads(read_text(path) or "{}")
    except ValueError:
        return {}
    out = {}
    prefix = "" if rel_dir == "." else rel_dir + "/"
    for key, meta in (data.get("packages") or {}).items():  # lockfileVersion 2/3
        for base in (prefix + "node_modules/", "node_modules/"):
            if key.startswith(base) and "/node_modules/" not in key[len(base):]:
                out.setdefault(key[len(base):].lower(), meta.get("version", ""))
    for name, meta in (data.get("dependencies") or {}).items():  # lockfileVersion 1
        if isinstance(meta, dict):
            out.setdefault(name.lower(), meta.get("version", ""))
    return out


def lock_pnpm(path, rel_dir):
    """pnpm-lock.yaml (v6+): importers.<rel_dir>.<deps-section>.<name>.version."""
    out, in_importers, importer, name = {}, False, None, None
    for line in read_text(path).splitlines():
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        s = line.strip()
        if indent == 0:
            in_importers = s == "importers:"
            importer = None
            continue
        if not in_importers:
            continue
        if indent == 2:
            importer = s.rstrip(":").strip("'\"")
        elif indent == 6 and importer == rel_dir:
            name = s.rstrip(":").strip("'\"").lower()
        elif indent == 8 and importer == rel_dir and name and s.startswith("version:"):
            out.setdefault(name, s.split(":", 1)[1].strip().strip("'\"").split("(")[0])
    return out


def lock_yarn(path):
    """yarn.lock v1 and Berry: header line of specs, then a version line."""
    out, names = {}, []
    for line in read_text(path).splitlines():
        if line and not line.startswith((" ", "#")) and line.rstrip().endswith(":"):
            names = [m.lower() for m in re.findall(r'"?(@?[^@\s",]+)@', line)]
        elif names and line.strip().startswith("version"):
            ver = line.strip()[len("version"):].strip(" :\"'")
            for n in names:
                out.setdefault(n, ver)
            names = []
    return out


def lock_composer(path):
    try:
        data = json.loads(read_text(path) or "{}")
    except ValueError:
        return {}
    return {pkg["name"].lower(): pkg.get("version", "")
            for key in ("packages", "packages-dev") for pkg in data.get(key) or [] if "name" in pkg}


def lock_gemfile(path):
    return {n.lower(): v for n, v in re.findall(r"^    ([A-Za-z0-9_.\-]+) \(([^)]+)\)$", read_text(path), re.M)}


def lock_nuget(path):
    try:
        data = json.loads(read_text(path) or "{}")
    except ValueError:
        return {}
    out = {}
    for framework_deps in (data.get("dependencies") or {}).values():
        for name, meta in framework_deps.items():
            out.setdefault(name.lower(), meta.get("resolved", ""))
    return out


def find_upwards(root, start, filename):
    """Nearest ancestor directory (up to the scan root) containing filename."""
    current = start
    while True:
        if os.path.isfile(os.path.join(current, filename)):
            return current
        if os.path.normcase(current) == os.path.normcase(root):
            return None
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def resolve_locked_versions(root, pdir, p):
    """Fill p['resolved'] = {dep: (version, lockfile)} from the nearest lockfile."""
    candidates = []
    if "js" in p["ecosystems"]:
        candidates += [("pnpm-lock.yaml", "pnpm"), ("package-lock.json", "npm"), ("yarn.lock", "yarn")]
    if "python" in p["ecosystems"]:
        candidates += [("uv.lock", "toml-py"), ("poetry.lock", "toml-py")]
    if "rust" in p["ecosystems"]:
        candidates += [("Cargo.lock", "toml")]
    if "php" in p["ecosystems"]:
        candidates += [("composer.lock", "composer")]
    if "ruby" in p["ecosystems"]:
        candidates += [("Gemfile.lock", "gem")]
    if "dotnet" in p["ecosystems"]:
        candidates += [("packages.lock.json", "nuget")]
    for lockname, kind in candidates:
        lock_dir = find_upwards(root, pdir, lockname)
        if not lock_dir:
            continue
        path = os.path.join(lock_dir, lockname)
        rel_dir = os.path.relpath(pdir, lock_dir).replace(os.sep, "/")
        if kind == "pnpm":
            versions = lock_pnpm(path, rel_dir)
        elif kind == "npm":
            versions = lock_package_json(path, rel_dir)
        elif kind == "yarn":
            versions = lock_yarn(path)
        elif kind == "toml-py":
            versions = lock_toml_packages(path, norm_py)
        elif kind == "toml":
            versions = lock_toml_packages(path)
        elif kind == "composer":
            versions = lock_composer(path)
        elif kind == "gem":
            versions = lock_gemfile(path)
        else:
            versions = lock_nuget(path)
        label = lockname if lock_dir == pdir else rel(root, path)
        for dep in p["deps"]:
            if dep in versions and versions[dep]:
                p["resolved"].setdefault(dep, (versions[dep], label))
        if versions:
            p["lockfiles_read"].append(label)
        break  # the first matching lockfile is authoritative


# ---------------------------------------------------------------- workspaces
def workspace_members(root):
    """Declared workspace/module members, resolved against the filesystem."""
    found = []

    def add(kind, patterns):
        dirs = []
        for pat in patterns:
            pat = pat.strip().strip("'\"").rstrip("/")
            if not pat or pat.startswith("!"):
                continue
            for match in sorted(glob.glob(os.path.join(root, *pat.split("/")))):
                if os.path.isdir(match):
                    dirs.append(rel(root, match))
        if patterns:
            found.append((kind, patterns, dirs))

    text = read_text(os.path.join(root, "pnpm-workspace.yaml"))
    if text:
        add("pnpm", re.findall(r"^\s*-\s*['\"]?([^'\"\n#]+)", text, re.M))
    try:
        pkg = json.loads(read_text(os.path.join(root, "package.json")) or "{}")
    except ValueError:
        pkg = {}
    ws = pkg.get("workspaces")
    if isinstance(ws, dict):
        ws = ws.get("packages")
    if isinstance(ws, list):
        add("npm/yarn workspaces", ws)
    text = read_text(os.path.join(root, "go.work"))
    if text:
        add("go.work", re.findall(r"^\s*(?:use\s+)?(\.[^\s()]*)\s*$", text, re.M))
    text = read_text(os.path.join(root, "Cargo.toml"))
    m = re.search(r"\[workspace\][^\[]*?members\s*=\s*\[([^\]]*)\]", text, re.S)
    if m:
        add("Cargo workspace", re.findall(r"""["']([^"']+)["']""", m.group(1)))
    for settings in ("settings.gradle", "settings.gradle.kts"):
        text = read_text(os.path.join(root, settings))
        if text:
            names = []
            for args in re.findall(r"^\s*include\s*\(?([^)\n]+)\)?", text, re.M):
                names += [n.strip(":").replace(":", "/") for n in re.findall(r"""["']([^"']+)["']""", args)]
            add("Gradle includes", names)
    return found


# ---------------------------------------------------------------- walk
def walk(root, max_depth):
    """Yield (dirpath, filenames) while pruning ignored directories."""
    count = 0
    root_depth = root.rstrip(os.sep).count(os.sep)
    for dirpath, dirnames, filenames in os.walk(root):
        depth = dirpath.rstrip(os.sep).count(os.sep) - root_depth
        if dirpath != root and "SKILL.md" in filenames:
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames
                       if not d.startswith(".") and d not in IGNORED_DIRS and depth < max_depth]
        count += len(filenames)
        yield dirpath, filenames
        if count > MAX_FILES:
            yield None, None
            return


def new_project():
    return {
        "ecosystems": set(), "manifests": [], "package_managers": [], "versions": [],
        "deps": {}, "dep_sources": {}, "notes": [], "commands": [],
        "markers": defaultdict(list), "matches": defaultdict(list),
        "extensions": Counter(), "resolved": {}, "lockfiles_read": [], "matched": set(),
    }


def detect(root, max_depth=DEFAULT_MAX_DEPTH):
    root = os.path.abspath(root)
    projects = {}
    files_by_dir = {}
    truncated = False
    for dirpath, filenames in walk(root, max_depth):
        if dirpath is None:
            truncated = True
            break
        files_by_dir[dirpath] = filenames
        manifest_hits = [(f, MANIFESTS[f]) for f in filenames if f in MANIFESTS]
        for pattern, eco in MANIFEST_GLOBS.items():
            manifest_hits += [(f, eco) for f in filenames if fnmatch.fnmatch(f, pattern)]
        if manifest_hits:
            p = projects.setdefault(dirpath, new_project())
            for f, eco in manifest_hits:
                p["ecosystems"].add(eco)
                p["manifests"].append(f)

    # Attribute source files to the nearest project directory (or root).
    project_dirs = sorted(projects, key=len, reverse=True)
    repo_ext = Counter()
    for dirpath, filenames in files_by_dir.items():
        owner = next((d for d in project_dirs if dirpath == d or dirpath.startswith(d + os.sep)), None)
        for f in filenames:
            ext = os.path.splitext(f)[1].lower()
            if ext in EXT_LANG:
                repo_ext[EXT_LANG[ext]] += 1
                if owner:
                    projects[owner]["extensions"][EXT_LANG[ext]] += 1

    for pdir, p in projects.items():
        files = set(files_by_dir.get(pdir, []))
        for f in sorted(p["manifests"]):
            path = os.path.join(pdir, f)
            parser = PARSERS.get(f)
            if parser is None and f.endswith((".csproj", ".fsproj", ".vbproj")):
                parser = deps_csproj
            elif parser is None and fnmatch.fnmatch(f, "requirements*.txt"):
                parser = deps_requirements
            if parser:
                for k, v in parser(path, p).items():
                    p["deps"].setdefault(k, v)
                    p["dep_sources"].setdefault(k, f)
        for extra in ("settings.gradle", "settings.gradle.kts"):
            if extra in files and extra not in p["manifests"]:
                for k, v in deps_gradle(os.path.join(pdir, extra), p).items():
                    p["deps"].setdefault(k, v)
                    p["dep_sources"].setdefault(k, extra)
        catalog = os.path.join(pdir, "gradle", "libs.versions.toml")
        if os.path.isfile(catalog):
            for k, v in deps_version_catalog(catalog).items():
                p["deps"].setdefault(k, v)
                p["dep_sources"].setdefault(k, "gradle/libs.versions.toml")
        resolve_locked_versions(root, pdir, p)
        for lock, pm in LOCKFILES:
            if lock in files:
                p["package_managers"].append("{} ({})".format(pm, lock))
        js_locks = {"pnpm-lock.yaml", "yarn.lock", "package-lock.json", "bun.lock", "bun.lockb", "deno.lock"}
        if "js" in p["ecosystems"] and not files & js_locks:
            shared = [rel(root, os.path.join(d, n)) for n in sorted(js_locks)
                      for d in [find_upwards(root, pdir, n)] if d]
            p["notes"].append("uses workspace lockfile {}".format(shared[0]) if shared
                              else "no JS lockfile found (dependencies unpinned or not installed)")
        if "pom.xml" in files:
            p["package_managers"].append("Maven (pom.xml)")
        if files & {"build.gradle", "build.gradle.kts"}:
            p["package_managers"].append("Gradle")
        for pin in VERSION_PINS:
            if pin in files:
                lines = read_text(os.path.join(pdir, pin)).strip().splitlines()
                p["versions"].append("{}: {}".format(pin, lines[0][:60] if lines else "(empty)"))
        for marker, cat, label in FILE_MARKERS:
            if exists_exact(pdir, marker):
                p["markers"][cat].append("{} ({})".format(label, marker))
        add_router_markers(pdir, p)
        add_prisma(pdir, p)
        add_config_db_signals(pdir, p)
        add_make_targets(pdir, files, p)
        match_rules(p)
    return root, projects, repo_ext, truncated


def evidence(p, dep):
    declared = p["deps"].get(dep) or ""
    declared = declared if declared and len(declared) < 30 else ""
    source = p["dep_sources"].get(dep, "?")
    if dep in p["resolved"]:
        version, lock = p["resolved"][dep]
        return "{} {} resolved in {}{}".format(dep, version, lock,
                                               "; declared {} in {}".format(declared, source) if declared else "")
    return "{}{} declared in {}".format(dep, " " + declared if declared else "", source)


def match_rules(p):
    for eco, cat, label, patterns in RULES:
        if eco not in p["ecosystems"]:
            continue
        for dep in p["deps"]:
            if any(fnmatch.fnmatchcase(dep, pat) for pat in patterns):
                p["matched"].add(dep)
                if not any(m[0] == label for m in p["matches"][cat]):
                    p["matches"][cat].append((label, evidence(p, dep)))


# Declared items that carry no stack meaning on their own.
UNINTERESTING_DEPS = re.compile(r"^(@types/|plugin:|sdk:|python$|php$|ext-)")


def unrecognized(p):
    return sorted(d for d in p["deps"] if d not in p["matched"] and not UNINTERESTING_DEPS.match(d))


def add_router_markers(pdir, p):
    if "next" not in p["deps"]:
        return
    for base in ("", "src"):
        for d, label in (("app", "App Router"), ("pages", "Pages Router")):
            if os.path.isdir(os.path.join(pdir, base, d)):
                p["markers"]["framework"].append("Next.js {} ({})".format(label, "/".join(x for x in (base, d) if x)))
    for mw in ("middleware.ts", "middleware.js", "src/middleware.ts", "src/middleware.js"):
        if os.path.isfile(os.path.join(pdir, *mw.split("/"))):
            p["markers"]["auth"].append("Next.js middleware ({})".format(mw))


def add_prisma(pdir, p):
    for cand in ("prisma/schema.prisma", "schema.prisma"):
        path = os.path.join(pdir, *cand.split("/"))
        if os.path.isfile(path):
            text = read_text(path)
            m = re.search(r"datasource\s+\w+\s*\{[^}]*provider\s*=\s*\"(\w+)\"", text, re.S)
            if m:
                db = PRISMA_PROVIDERS.get(m.group(1).lower(), m.group(1))
                p["markers"]["database"].append("{} (Prisma datasource provider in {})".format(db, cand))
            return


def add_config_db_signals(pdir, p):
    """Report only connection schemes from example env files and app config."""
    candidates = list(ENV_EXAMPLES)
    res = os.path.join(pdir, "src", "main", "resources")
    if os.path.isdir(res):
        candidates += ["src/main/resources/" + f for f in os.listdir(res)
                       if f.startswith("application") and f.endswith((".yml", ".yaml", ".properties"))]
    for f in ("appsettings.json", "appsettings.Development.json", "config/database.yml",
              "settings.py", "config/settings.py"):
        candidates.append(f)
    for name in os.listdir(pdir):
        if os.path.isdir(os.path.join(pdir, name, "settings")):
            candidates += [name + "/settings/" + f for f in ("base.py", "__init__.py", "common.py")]
        if os.path.isfile(os.path.join(pdir, name, "settings.py")):
            candidates.append(name + "/settings.py")
    seen = set()
    for c in candidates:
        path = os.path.join(pdir, *c.split("/"))
        if not os.path.isfile(path):
            continue
        text = read_text(path)
        for rx, db in URL_SCHEMES:
            if rx.search(text) and (db, c) not in seen:
                seen.add((db, c))
                p["markers"]["database"].append("{} (connection scheme in {})".format(db, c))
        for engine in re.findall(r"django\.db\.backends\.(\w+)", text):
            label = DJANGO_ENGINES.get(engine, engine)
            if (label, c) not in seen:
                seen.add((label, c))
                p["markers"]["database"].append("{} (Django ENGINE in {})".format(label, c))
        if c.startswith("config/database.yml"):
            for adapter in re.findall(r"adapter:\s*(\w+)", text):
                p["markers"]["database"].append("{} (Rails adapter in {})".format(adapter, c))


def add_make_targets(pdir, files, p):
    for mk in ("Makefile", "makefile", "GNUmakefile", "justfile", "Justfile", "Taskfile.yml"):
        if mk in files:
            text = read_text(os.path.join(pdir, mk))
            if mk.lower().startswith("taskfile"):
                targets = re.findall(r"^  ([A-Za-z0-9_.:\-]+):\s*$", text, re.M)
            else:
                targets = re.findall(r"^([A-Za-z0-9_.\-]+)\s*:(?!=)", text, re.M)
            targets = [t for t in dict.fromkeys(targets) if not t.startswith(".")][:20]
            if targets:
                p["commands"].append("{} targets: {}".format(mk, ", ".join(targets)))


def repo_signals(root):
    out = {"monorepo": [], "ci": [], "containers": [], "compose_services": [],
           "convention_docs": [], "workspaces": workspace_members(root)}
    for f, label in ROOT_MARKERS:
        if os.path.exists(os.path.join(root, f)):
            out["monorepo"].append("{} ({})".format(label, f))
    for c in CI_PATHS:
        path = os.path.join(root, *c.split("/"))
        if os.path.isdir(path):
            out["ci"] += [c + "/" + f for f in sorted(os.listdir(path)) if f.endswith((".yml", ".yaml"))]
        elif os.path.isfile(path):
            out["ci"].append(c)
    for doc in CONVENTION_DOCS:
        if os.path.exists(os.path.join(root, *doc.split("/"))):
            out["convention_docs"].append(doc)
    for f in sorted(os.listdir(root)):
        lower = f.lower()
        if lower.startswith("dockerfile") or lower.endswith(".dockerfile"):
            out["containers"].append(f)
        if re.match(r"^(docker-)?compose(\.[\w-]+)?\.ya?ml$", lower):
            out["containers"].append(f)
            for image in re.findall(r"""^\s*image:\s*["']?([^\s"'#]+)""", read_text(os.path.join(root, f)), re.M):
                name = image.split("/")[-1].split(":")[0].lower()
                for key, label in IMAGE_DB:
                    if key in name:
                        out["compose_services"].append("{} (image {} in {})".format(label, image, f))
                        break
    return out


# ---------------------------------------------------------------- output
CATEGORY_TITLES = [
    ("framework", "Frameworks"), ("database", "Databases"), ("data_access", "Data access"),
    ("migrations", "Migrations"), ("testing", "Testing"), ("validation", "Validation"),
    ("auth", "Auth"), ("state", "Client state / data fetching"), ("logging", "Logging"),
    ("tooling", "Tooling"), ("other", "Other"),
]


def to_report(root, projects, repo_ext, truncated, repo):
    out = {"root": root, "truncated": truncated, "repository": repo,
           "source_files_by_language": dict(repo_ext.most_common(8)), "projects": []}
    for pdir in sorted(projects, key=lambda d: (d.count(os.sep), d)):
        p = projects[pdir]
        entry = {
            "path": rel(root, pdir),
            "ecosystems": sorted(LANG_NAMES.get(e, e) for e in p["ecosystems"]),
            "manifests": sorted(p["manifests"]),
            "source_files_by_language": dict(p["extensions"].most_common(5)),
            "package_managers": list(dict.fromkeys(p["package_managers"])),
            "versions": list(dict.fromkeys(p["versions"])),
            "declared_dependencies": len(p["deps"]),
            "lockfiles_read": p["lockfiles_read"],
            "unrecognized_dependencies": unrecognized(p),
            "commands": p["commands"],
            "notes": list(dict.fromkeys(p["notes"]))[:15],
        }
        for cat, _ in CATEGORY_TITLES:
            items = ["{} [{}]".format(label, ev) for label, ev in p["matches"].get(cat, [])]
            items += p["markers"].get(cat, [])
            if items:
                entry[cat] = list(dict.fromkeys(items))
        out["projects"].append(entry)
    detected = {pr["path"] for pr in out["projects"]}
    out["workspaces"] = []
    for kind, patterns, dirs in repo.pop("workspaces"):
        out["workspaces"].append({
            "kind": kind, "patterns": patterns, "members": dirs,
            "members_without_detected_manifest": [d for d in dirs if d not in detected],
        })
    return out


def print_markdown(report):
    w = sys.stdout.write
    w("# Stack signals: {}\n\n".format(report["root"]))
    w("Evidence to verify against source code - not conclusions. Declared dependencies\n"
      "may be unused; confirm frameworks via entry points and imports.\n\n")
    if report["truncated"]:
        w("**Walk truncated at {} files; results are partial.**\n\n".format(MAX_FILES))
    repo = report["repository"]
    w("## Repository\n")
    langs = ", ".join("{} {}".format(k, v) for k, v in report["source_files_by_language"].items())
    w("- Source files by language: {}\n".format(langs or "none found"))
    for key, title in (("monorepo", "Monorepo markers"), ("ci", "CI config"),
                       ("containers", "Container files"), ("compose_services", "Compose services"),
                       ("convention_docs", "Convention docs")):
        if repo[key]:
            w("- {}: {}\n".format(title, "; ".join(repo[key])))
    for ws in report["workspaces"]:
        w("- Workspace ({}): {} -> {}\n".format(
            ws["kind"], ", ".join(ws["patterns"]), ", ".join(ws["members"]) or "no matching directories"))
        if ws["members_without_detected_manifest"]:
            w("  - Not scanned or no manifest (raise --max-depth?): {}\n".format(
                ", ".join(ws["members_without_detected_manifest"])))
    if not report["projects"]:
        w("\nNo recognized manifests found. Inspect the source tree and build scripts manually.\n")
    for pr in report["projects"]:
        w("\n## Project: {}\n".format(pr["path"]))
        w("- Ecosystem: {} (manifests: {})\n".format(", ".join(pr["ecosystems"]), ", ".join(pr["manifests"])))
        if pr["source_files_by_language"]:
            w("- Source files: {}\n".format(", ".join("{} {}".format(k, v) for k, v in pr["source_files_by_language"].items())))
        if pr["package_managers"]:
            w("- Build / package manager: {}\n".format("; ".join(pr["package_managers"])))
        if pr["versions"]:
            w("- Versions: {}\n".format("; ".join(pr["versions"])))
        for cat, title in CATEGORY_TITLES:
            if pr.get(cat):
                w("- {}: {}\n".format(title, "; ".join(pr[cat])))
        if pr["commands"]:
            w("- Commands: {}\n".format(" | ".join(pr["commands"])))
        if pr["notes"]:
            w("- Notes: {}\n".format("; ".join(pr["notes"])))
        if pr["lockfiles_read"]:
            w("- Resolved versions from: {}\n".format(", ".join(pr["lockfiles_read"])))
        unknown = pr["unrecognized_dependencies"]
        w("- Declared dependencies: {}; not recognized by this script ({}): {}\n".format(
            pr["declared_dependencies"], len(unknown),
            ", ".join(unknown[:UNRECOGNIZED_SHOWN]) + (" (+{} more)".format(len(unknown) - UNRECOGNIZED_SHOWN)
                                                     if len(unknown) > UNRECOGNIZED_SHOWN else "")
            if unknown else "none"))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Collect technology-stack signals from a repository.")
    ap.add_argument("root", nargs="?", default=".", help="repository root (default: current directory)")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of Markdown")
    ap.add_argument("--max-depth", type=int, default=DEFAULT_MAX_DEPTH,
                    help="maximum directory depth to scan (default: %(default)s)")
    args = ap.parse_args(argv)
    if not os.path.isdir(args.root):
        sys.stderr.write("error: {} is not a directory\n".format(args.root))
        return 2
    root, projects, repo_ext, truncated = detect(args.root, args.max_depth)
    report = to_report(root, projects, repo_ext, truncated, repo_signals(root))
    if args.json:
        json.dump(report, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        print_markdown(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
