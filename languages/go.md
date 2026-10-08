# Go

## Contents
- Detect
- Standard library first
- Errors
- Context
- Concurrency
- Package structure
- Data access
- Testing
- Verification commands

## Detect

- Go version from the `go` directive in `go.mod` (and `toolchain`). Don't use language or stdlib features newer than that version (for example generics, range-over-int, newer `net/http` routing patterns, `slices`/`maps` packages).
- Module path from `go.mod`, used for imports. `go.work` means a multi-module workspace.
- Web layer: [go-web](../frameworks/go-web.md). Data access: `database/sql`, pgx, sqlx, sqlc, GORM, ent, Bun.

## Standard library first

Go codebases tend to prefer the standard library and few dependencies. Before adding a module, check whether the stdlib or an existing dependency covers it (`net/http`, `encoding/json`, `log/slog`, `context`, `errors`, `testing`). Add modules with `go get` and keep `go.mod`/`go.sum` tidy (`go mod tidy`).

## Errors

- Return errors. Don't panic in library or request code (panics are for truly unrecoverable programmer errors, and the project may have recovery middleware).
- Wrap with context using `fmt.Errorf("doing X: %w", err)`. Inspect with `errors.Is`/`errors.As`. Follow existing sentinel errors (`var ErrNotFound = errors.New(...)`) and custom error types.
- Handle each error once: either log it or return it, not both at every layer.
- Map domain errors to HTTP status in the handler layer, the way existing handlers do.

## Context

- Accept `ctx context.Context` as the first parameter for anything doing I/O. Pass the request context through to DB and HTTP calls so that cancellation and deadlines propagate.
- Don't store contexts in structs. Don't use `context.Background()` inside request paths.
- Use context values only for request-scoped data the project already carries this way (request ID, auth principal), with typed keys.

## Concurrency

- Every goroutine needs a clear exit path (context cancellation, closed channel, `WaitGroup`). Avoid leaks.
- Bound concurrency (worker pools, semaphores, `errgroup.SetLimit` if `errgroup` is used).
- Protect shared state with mutexes or confine it to one goroutine. Run tests with `-race` when the project supports it.
- Don't add goroutines to request handlers unless there's a measured or clear benefit.

## Package structure

- Follow the existing layout (`cmd/`, `internal/`, `pkg/`, or flat; packages by domain vs by layer). `internal/` enforces import boundaries.
- Package names are short, lowercase, and without stutter (`user.Service`, not `user.UserService`), unless the codebase has a different established style.
- Accept interfaces, return concrete types. Define small interfaces at the consumer where the project does that for testing seams.
- Dependency wiring is usually explicit in `main` (or uses wire/fx if present). Follow it.

## Data access

- `database/sql`/pgx/sqlx: always pass `ctx`, close `rows` (`defer rows.Close()`), check `rows.Err()`, use placeholders (`$1` for Postgres, `?` for MySQL/SQLite, depending on the driver).
- sqlc: edit `.sql` query files, then regenerate. Never hand-edit generated code.
- GORM/ent/Bun: follow the existing model and query patterns. Watch for N+1 with associations (`Preload`).
- Transactions: use the project's helper (for example a `WithTx` function). Make sure rollback happens on error.

## Testing

- Standard `testing` package with table-driven tests and `t.Run` subtests, typically. Use testify/gomock/mockery only if they're already present.
- HTTP handlers: `net/http/httptest` (`httptest.NewRecorder`, `httptest.NewServer`), or the framework's test utilities used by neighbors.
- Test files sit next to the code (`foo_test.go`). Package `foo` vs `foo_test` (black-box testing): match the neighbors.
- Integration tests may use build tags (`//go:build integration`) or env guards. Follow the existing ones.

## Verification commands

`go build ./...`, `go vet ./...`, `go test ./path/to/pkg/...` (add `-run TestName`, `-race`), `gofmt -l .` (or `goimports`), and `golangci-lint run` if configured. Use Makefile targets if CI uses them.
