# Design note: stack-aware-development

Written before implementation from a review of the skills.sh directory, the Agent Skills specification (agentskills.io), and the Claude skill-authoring best practices. Install counts are approximate.

## The problem

Coding agents often make technology assumptions. They write Express-style middleware in a Spring Boot service, suggest `npm install` in a pnpm workspace, add a second ORM next to an existing one, or install an auth library in an app that already has authentication. The model usually knows the right idioms. What goes wrong is that it never checks which idioms apply to the repository in front of it.

## What already exists (and covers its area well)

| Area | Representative skills | What they do well |
|------|----------------------|-------------------|
| Process discipline | `systematic-debugging`, `test-driven-development`, `verification-before-completion` (obra/superpowers); `diagnose`, `tdd`, `qa` (mattpocock/skills) | Debugging, TDD, and verification loops that work in any language |
| Architecture critique | `improve-codebase-architecture`, `codebase-design` (mattpocock/skills); `architecture-patterns` (wshobson/agents) | Opinionated architectural improvement |
| Code review | `code-review` (mattpocock), `requesting-code-review` (obra), `code-review-and-quality` (addyosmani) | Review checklists and review workflow |
| Grounding | `grounding-before-coding` (riekelt/principal-engineer) | "Read the code before claiming things." Evidence discipline. It depends on a companion skill and has no stack detection or stack-specific routing. |
| Stack documentation | `technology-stack-blueprint-generator` (github/awesome-copilot), `codebase-onboarding` (affaan-m/ecc) | Produce a document (a blueprint or CLAUDE.md). They don't shape the change being made. |
| Fixed conventions | `codebase-conventions` (ilamanov/skills), `coding-standards` (affaan-m/ecc) | Apply the author's preferred conventions, which is the opposite of learning the repository's conventions |
| Single-stack depth | `vercel-react-best-practices`, `supabase-postgres-best-practices`, `golang-*` (samber), `fastapi` (fastapi/fastapi), `nestjs-best-practices`, `fastify-best-practices`, `java-coding-standards`, PlanetScale `postgres`/`mysql` | Deep knowledge of one technology. They assume you already know you're in that stack. |
| Generic full-stack | `fullstack-guardian` (jeffallan), `fullstack-developer`, `senior-fullstack` | Feature workflows, mostly built around a JS/TS web stack |

## The gap

No skill on the directory does all of the following in one workflow:

1. Detects the stack from evidence (manifests, lockfiles, config, imports), keeps the database separate from the data-access layer, and handles monorepos package by package.
2. Learns the repository's own conventions by finding the closest existing example and copying its shape, rather than applying a preset style.
3. Classifies the task and loads only the guidance relevant to that stack and that task.
4. Gives way to specialized skills when the environment has them, and still works when it doesn't.

`stack-aware-development` is the layer that answers "what am I working in, and which guidance applies?" It doesn't try to be the deep Next.js, PostgreSQL, or security expert.

## Why install it alongside specialized skills

- Specialized skills only fire once the agent already knows the stack. This skill makes sure the stack is identified correctly first, which matters most in polyglot repos and monorepos.
- Specialized skills teach the ideal version of a framework. This skill makes the repository's existing patterns win over that ideal, unless there is a correctness or security reason to deviate.
- Users can't install a skill for every technology they touch. This skill gives a reasonable baseline for common stacks and an honest fallback for the rest.

## V1 scope

- `SKILL.md`: the workflow, evidence rules, the "nearest neighbor" convention technique, a task-to-reference routing table, composition rules, and verification and reporting.
- `references/`: cross-cutting engineering concerns, each loaded only when the task needs it: stack detection, conventions, architecture, API design, authentication, authorization, database (with engine notes), testing, debugging, security, performance, and code review.
- `languages/`: JS/TS, Java/Kotlin, Python, Go, C#/.NET, Rust, plus a fallback file for everything else (PHP and Ruby notes included).
- `frameworks/`: Next.js/React, Node (Express/Fastify/NestJS), Spring Boot, FastAPI/Django/Flask, ASP.NET Core, Go web.
- `scripts/detect_stack.py`: optional, stdlib-only. It collects stack signals deterministically and skips vendored and agent-skill directories. It reports evidence, not conclusions.
- `scripts/validate_skill.py`: a maintainer check for frontmatter, links, orphaned files, and the eval schema.
- `evals/evals.json`: behavioral scenarios compatible with the skill-creator schema. `evals/trigger-evals.json` is for tuning the description.

Decisions:

- **Database engine notes go in one file** (`references/database.md`) instead of a `databases/` directory. Engine notes are short, and database tasks nearly always need the general guidance too.
- **No fixture files inside the skill.** When the skill is installed under `.claude/skills/`, a fixture `pom.xml` or `package.json` would itself become a false stack signal for the host project. Fixture repositories are packed into `evals/fixtures.json` instead, and `evals/build_fixtures.py` unpacks them into git repositories outside the skill.
- **Spec-only frontmatter** (`name`, `description`, `license`, `metadata`) so the skill stays portable across agents.

## Left for V2

- Dedicated framework files for Vue/Nuxt, Angular, Svelte, Laravel, Symfony, Rails, Quarkus/Micronaut, Ktor, Actix/Axum, and mobile (Android, iOS, Flutter, React Native).
- Infrastructure-as-code awareness (Terraform, Helm, Kubernetes manifests) as first-class stacks.
- Repeated benchmark runs across several models, with real toolchains and messier fixtures. A first single-run comparison is in `evals/BENCHMARK.md`.
- Better `detect_stack.py` coverage: Bazel and Nx project graphs, and resolved versions for Maven/Gradle, which come from BOMs rather than lockfiles.
- Optionally caching a stack profile per repository between sessions, if hosts support persistent memory.
