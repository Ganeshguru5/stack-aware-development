"""Unit tests for scripts/detect_stack.py.

Fixture repositories are written to temporary directories at test time, so no
project manifests live inside the skill (they would become false stack
signals once the skill is installed in a host project).

Run: python -m unittest discover -s tests
"""
import io
import json
import os
import sys
import tempfile
import textwrap
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import detect_stack  # noqa: E402


def write_tree(root, files):
    for rel, content in files.items():
        path = os.path.join(root, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(textwrap.dedent(content).lstrip("\n"))


def scan(files, max_depth=detect_stack.DEFAULT_MAX_DEPTH):
    with tempfile.TemporaryDirectory() as tmp:
        write_tree(tmp, files)
        buf = io.StringIO()
        with redirect_stdout(buf):
            detect_stack.main([tmp, "--json", "--max-depth", str(max_depth)])
        return json.loads(buf.getvalue())


def project(report, path="."):
    for pr in report["projects"]:
        if pr["path"] == path:
            return pr
    raise AssertionError("project {!r} not found in {}".format(path, [p["path"] for p in report["projects"]]))


def joined(pr, category):
    return " | ".join(pr.get(category, []))


class JvmTests(unittest.TestCase):
    def test_spring_boot_maven(self):
        pr = project(scan({
            "pom.xml": """
                <project xmlns="http://maven.apache.org/POM/4.0.0">
                  <parent><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-parent</artifactId><version>3.3.0</version></parent>
                  <properties><java.version>21</java.version></properties>
                  <dependencies>
                    <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-web</artifactId></dependency>
                    <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-data-jpa</artifactId></dependency>
                    <dependency><groupId>org.postgresql</groupId><artifactId>postgresql</artifactId></dependency>
                    <dependency><groupId>org.flywaydb</groupId><artifactId>flyway-core</artifactId></dependency>
                    <dependency><groupId>com.example</groupId><artifactId>internal-sdk</artifactId></dependency>
                  </dependencies>
                </project>""",
            "mvnw": "",
            "src/main/resources/application.yml": "spring:\n  datasource:\n    url: jdbc:postgresql://db/app\n",
        }))
        self.assertIn("Spring Boot", joined(pr, "framework"))
        self.assertIn("Spring MVC", joined(pr, "framework"))
        self.assertIn("PostgreSQL", joined(pr, "database"))
        self.assertIn("JPA / Hibernate", joined(pr, "data_access"))
        self.assertIn("Flyway", joined(pr, "migrations"))
        self.assertIn("java 21 (pom java.version)", pr["versions"])
        self.assertIn("com.example:internal-sdk", pr["unrecognized_dependencies"])

    def test_gradle_kotlin_and_includes(self):
        report = scan({
            "settings.gradle.kts": 'rootProject.name = "shop"\ninclude(":api", ":core")\n',
            "api/build.gradle.kts": """
                plugins { kotlin("jvm") version "2.0.0"; id("org.springframework.boot") version "3.3.0" }
                dependencies { testImplementation("io.mockk:mockk:1.13.11") }""",
            "core/build.gradle.kts": "plugins { kotlin(\"jvm\") }\n",
        })
        api = project(report, "api")
        self.assertIn("Spring Boot", joined(api, "framework"))
        self.assertIn("MockK", joined(api, "testing"))
        self.assertIn("Kotlin", joined(api, "other"))
        ws = [w for w in report["workspaces"] if w["kind"] == "Gradle includes"]
        self.assertEqual(ws[0]["members"], ["api", "core"])


class JavaScriptTests(unittest.TestCase):
    NEXT_PKG = """
        {"name": "web", "packageManager": "pnpm@9.12.0",
         "scripts": {"test": "vitest run", "typecheck": "tsc --noEmit"},
         "dependencies": {"next": "^15.0.0", "react": "^19.0.0", "@prisma/client": "^6.0.0", "left-pad": "1.3.0"},
         "devDependencies": {"vitest": "^2.1.0", "@types/node": "^22.0.0"}}"""

    def test_next_with_pnpm_resolved_versions(self):
        pr = project(scan({
            "package.json": self.NEXT_PKG,
            "pnpm-lock.yaml": """
                lockfileVersion: '9.0'

                importers:

                  .:
                    dependencies:
                      next:
                        specifier: ^15.0.0
                        version: 15.1.3(react-dom@19.0.0(react@19.0.0))(react@19.0.0)
                      react:
                        specifier: ^19.0.0
                        version: 19.0.0

                packages:

                  next@15.1.3:
                    resolution: {integrity: sha512-abc}
                """,
            "app/page.tsx": "export default function Page() { return null }\n",
            "prisma/schema.prisma": 'datasource db {\n  provider = "postgresql"\n  url = env("DATABASE_URL")\n}\n',
        }))
        self.assertIn("next 15.1.3 resolved in pnpm-lock.yaml", joined(pr, "framework"))
        self.assertIn("App Router", joined(pr, "framework"))
        self.assertIn("PostgreSQL (Prisma datasource provider", joined(pr, "database"))
        self.assertIn("pnpm (pnpm-lock.yaml)", pr["package_managers"])
        self.assertEqual(pr["unrecognized_dependencies"], ["left-pad"])  # @types/* filtered
        self.assertTrue(any(c.startswith("script typecheck") for c in pr["commands"]))

    def test_npm_lockfile_v3(self):
        pr = project(scan({
            "package.json": '{"dependencies": {"express": "^4.19.0"}}',
            "package-lock.json": json.dumps({"lockfileVersion": 3, "packages": {
                "": {"dependencies": {"express": "^4.19.0"}},
                "node_modules/express": {"version": "4.21.2"},
                "node_modules/express/node_modules/debug": {"version": "2.6.9"}}}),
        }))
        self.assertIn("express 4.21.2 resolved in package-lock.json", joined(pr, "framework"))

    def test_yarn_lock(self):
        pr = project(scan({
            "package.json": '{"dependencies": {"fastify": "^4.0.0"}}',
            "yarn.lock": '"fastify@^4.0.0":\n  version "4.28.1"\n  resolved "https://example.invalid/fastify.tgz"\n',
        }))
        self.assertIn("fastify 4.28.1 resolved in yarn.lock", joined(pr, "framework"))

    def test_monorepo_workspace_scoping_and_decoys(self):
        report = scan({
            "package.json": '{"name": "root", "private": true}',
            "pnpm-workspace.yaml": "packages:\n  - 'services/*'\n  - 'apps/*'\n",
            "pnpm-lock.yaml": """
                lockfileVersion: '9.0'
                importers:
                  .:
                    devDependencies:
                      turbo:
                        specifier: ^2.0.0
                        version: 2.1.0
                  services/billing:
                    dependencies:
                      '@nestjs/core':
                        specifier: ^10.0.0
                        version: 10.4.1
                """,
            "services/billing/package.json": '{"dependencies": {"@nestjs/core": "^10.0.0", "typeorm": "^0.3.0", "mysql2": "^3.0.0"}}',
            "apps/web/README.md": "no manifest here yet\n",
            # Decoys: must never be reported as host-project evidence.
            ".claude/skills/other/pom.xml": "<project><dependencies><dependency><groupId>io.quarkus</groupId><artifactId>quarkus-core</artifactId></dependency></dependencies></project>",
            "tools/some-skill/SKILL.md": "---\nname: some-skill\n---\n",
            "tools/some-skill/package.json": '{"dependencies": {"koa": "2"}}',
            "node_modules/express/package.json": '{"dependencies": {"debug": "2"}}',
            ".env": "DATABASE_URL=mongodb://admin:TOPSECRET@prod.invalid/db\n",
        })
        billing = project(report, "services/billing")
        self.assertIn("@nestjs/core 10.4.1 resolved in pnpm-lock.yaml", joined(billing, "framework"))
        self.assertIn("MySQL", joined(billing, "database"))
        self.assertIn("uses workspace lockfile pnpm-lock.yaml", billing["notes"])
        self.assertEqual(sorted(p["path"] for p in report["projects"]), [".", "services/billing"])
        ws = report["workspaces"][0]
        self.assertEqual(ws["kind"], "pnpm")
        self.assertEqual(ws["members_without_detected_manifest"], ["apps/web"])
        dump = json.dumps(report)
        for leaked in ("Quarkus", "Koa", "Express", "TOPSECRET", "MongoDB"):
            self.assertNotIn(leaked, dump)


class PythonTests(unittest.TestCase):
    def test_pyproject_sections_and_uv_lock(self):
        pr = project(scan({
            "pyproject.toml": """
                [project]
                name = "orders"
                description = "django-free service"
                requires-python = ">=3.11"
                dependencies = [
                  "fastapi>=0.110",
                  "sqlalchemy[asyncio]>=2.0",
                  "uvicorn[standard]",
                  "asyncpg",
                ]

                [dependency-groups]
                dev = ["pytest", "pytest-asyncio"]

                [tool.ruff]
                line-length = 100
                """,
            "uv.lock": '[[package]]\nname = "fastapi"\nversion = "0.115.6"\n\n[[package]]\nname = "SQLAlchemy"\nversion = "2.0.36"\n',
        }))
        self.assertIn("fastapi 0.115.6 resolved in uv.lock", joined(pr, "framework"))
        self.assertIn("sqlalchemy 2.0.36 resolved in uv.lock", joined(pr, "data_access"))
        self.assertNotIn("Django", joined(pr, "framework"))
        self.assertIn("pytest", joined(pr, "testing"))
        self.assertIn("python >=3.11 (requires-python)", pr["versions"])
        self.assertIn("uvicorn", pr["unrecognized_dependencies"])
        self.assertNotIn("line-length", pr["unrecognized_dependencies"])

    def test_poetry_tables(self):
        pr = project(scan({
            "pyproject.toml": """
                [tool.poetry.dependencies]
                python = "^3.11"
                Django = "^5.0"
                djangorestframework = "^3.15"

                [tool.poetry.group.dev.dependencies]
                pytest-django = "^4.8"
                """,
            "poetry.lock": '[[package]]\nname = "django"\nversion = "5.1.4"\n',
            "proj/settings.py": "DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql'}}\n",
        }))
        self.assertIn("django 5.1.4 resolved in poetry.lock", joined(pr, "framework"))
        self.assertIn("Django REST Framework", joined(pr, "framework"))
        self.assertIn("PostgreSQL (Django ENGINE", joined(pr, "database"))
        self.assertTrue(any("Poetry" in pm for pm in pr["package_managers"]))


class OtherEcosystemTests(unittest.TestCase):
    def test_go_gin_pgx(self):
        pr = project(scan({
            "go.mod": "module example.com/shop\n\ngo 1.22\n\nrequire (\n\tgithub.com/gin-gonic/gin v1.10.0\n\tgithub.com/jackc/pgx/v5 v5.6.0\n)\n",
            "migrations/000001_init.up.sql": "SELECT 1;\n",
            "Makefile": "test:\n\tgo test ./...\n",
        }))
        self.assertIn("Gin", joined(pr, "framework"))
        self.assertIn("pgx", joined(pr, "data_access"))
        self.assertIn("go 1.22 (go.mod)", pr["versions"])
        self.assertIn("Makefile targets: test", pr["commands"])
        # Case-sensitive marker check: 'migrations/' is not EF Core 'Migrations/'.
        self.assertNotIn("EF Core", joined(pr, "migrations"))

    def test_dotnet_csproj(self):
        pr = project(scan({
            "Api/Api.csproj": """
                <Project Sdk="Microsoft.NET.Sdk.Web">
                  <PropertyGroup><TargetFramework>net8.0</TargetFramework><Nullable>enable</Nullable></PropertyGroup>
                  <ItemGroup>
                    <PackageReference Include="Microsoft.EntityFrameworkCore.SqlServer" Version="8.0.8" />
                    <PackageReference Include="FluentValidation.AspNetCore" Version="11.3.0" />
                  </ItemGroup>
                </Project>""",
        }), "Api")
        self.assertIn("ASP.NET Core", joined(pr, "framework"))
        self.assertIn("SQL Server", joined(pr, "database"))
        self.assertIn("Entity Framework Core", joined(pr, "data_access"))
        self.assertIn("FluentValidation", joined(pr, "validation"))

    def test_cargo_workspace_and_lock(self):
        report = scan({
            "Cargo.toml": '[workspace]\nmembers = ["crates/api"]\n',
            "Cargo.lock": '[[package]]\nname = "axum"\nversion = "0.7.9"\n',
            "crates/api/Cargo.toml": '[package]\nname = "api"\nedition = "2021"\n\n[dependencies]\naxum = "0.7"\nsqlx = { version = "0.8", features = ["postgres"] }\n',
        })
        api = project(report, "crates/api")
        self.assertIn("axum 0.7.9 resolved in Cargo.lock", joined(api, "framework"))
        self.assertIn("SQLx", joined(api, "data_access"))
        self.assertEqual(report["workspaces"][0]["members"], ["crates/api"])

    def test_ruby_and_php_locks(self):
        ruby = project(scan({
            "Gemfile": "source 'https://rubygems.org'\ngem 'rails', '~> 7.1'\ngem 'pg'\n",
            "Gemfile.lock": "GEM\n  specs:\n    pg (1.5.9)\n    rails (7.1.5)\n",
        }))
        self.assertIn("rails 7.1.5 resolved in Gemfile.lock", joined(ruby, "framework"))
        php = project(scan({
            "composer.json": '{"require": {"php": "^8.2", "laravel/framework": "^11.0"}}',
            "composer.lock": '{"packages": [{"name": "laravel/framework", "version": "v11.36.1"}]}',
        }))
        self.assertIn("laravel/framework v11.36.1 resolved in composer.lock", joined(php, "framework"))

    def test_clojure_general_support(self):
        pr = project(scan({
            "deps.edn": '{:deps {metosin/reitit {:mvn/version "0.7.2"}}}\n',
            "src/app/core.clj": "(ns app.core)\n",
        }))
        self.assertEqual(pr["ecosystems"], ["Clojure"])
        self.assertEqual(pr["source_files_by_language"], {"Clojure": 1})

    def test_empty_repo(self):
        report = scan({"README.md": "# nothing\n"})
        self.assertEqual(report["projects"], [])


if __name__ == "__main__":
    unittest.main()
