# Testing

## Contents
- Detect the existing test setup
- What to test
- Choosing the test level
- Writing tests that fit
- Running tests

## Detect the existing test setup

Find, before writing any test:
- **Framework and runner**: from config files, dev dependencies, and CI commands (see [stack-detection.md](stack-detection.md)).
- **Layout**: co-located (`foo.test.ts`, `foo_test.go`) or a mirrored tree (`src/test/java`, `tests/`); unit vs. integration separation (directories, tags/markers, separate tasks).
- **Helpers**: fixtures, factories/builders, test-data seeds, custom assertions, auth helpers, HTTP test clients, DB setup and teardown.
- **Mocking style**: the mocking library in use, fakes vs. mocks, HTTP mocking (MSW, WireMock, `responses`/`respx`, `httptest`), whether the DB is mocked or real.

Don't introduce a new test framework, assertion library, or mocking library. If the project has no tests at all, use the ecosystem's standard tool (Go `testing`, pytest, JUnit 5, the runner matching the JS build tool, xUnit or whatever .NET template the project derives from, Rust built-in tests), and say that you set it up.

## What to test

Prioritize by risk:
1. **Regression**: for bug fixes, a test that fails before the fix and passes after it.
2. **Behavior of the change**: the main success path through the public interface (API, function, component).
3. **Failure paths**: validation errors, not found, unauthorized/forbidden, conflicts, downstream failures.
4. **Boundaries**: empty, one, many; limits (max page size, max length); nulls; time zones and dates; Unicode; numeric edges. For input parsing (pagination, filters), cover each invalid input class the code rejects, not just one.
5. **Integration points**: queries against a real engine, serialization contracts, auth wiring, transactions.

Don't pad with tests for trivial getters or for framework behavior.

## Choosing the test level

| Change | Typical level |
|--------|---------------|
| Pure logic / calculation | Unit |
| Endpoint behavior, validation, status codes | The framework's HTTP/integration test style used by neighbors (e.g. MockMvc/WebTestClient, `TestClient`/`httpx`, Supertest, `httptest`, `WebApplicationFactory`) |
| Query correctness or performance | Integration against the real engine, if the project supports it |
| Auth/permission rules | Integration through the real security config |
| UI behavior | Component tests with the project's library. E2E only if the project already has an E2E suite and the flow is critical. |
| Migrations | Run up (and down, if supported) against a populated test DB when possible |

Match how the neighboring feature is tested. If neighbors have both unit and integration tests, add both.

## Writing tests that fit

- Name and place files like the neighbors. Reuse their fixtures and factories, and extend shared fixtures rather than duplicating them.
- Arrange data explicitly in the test. Avoid depending on order or on leftover state from other tests.
- Assert observable behavior (responses, persisted state, emitted events), not implementation details or call counts, unless the codebase tests that way.
- Keep tests deterministic: control time, randomness, and concurrency with the project's existing utilities (fake clocks, seeded randomness).
- Don't weaken or delete existing tests to make a change pass. If an existing test is wrong, explain why before changing it.

## Running tests

- Use the project's command (package scripts, Gradle/Maven tasks, `make test`, `pytest` with the project's options, `go test ./...`, `dotnet test`, `cargo test`).
- Start narrow (the single file or test), then widen to the affected module, then the full suite if shared code changed.
- If tests need services (DB, broker), use the project's compose/Testcontainers setup. If that isn't possible in the current environment, report which tests couldn't run.
- Report real results. Never claim tests pass without running them.
