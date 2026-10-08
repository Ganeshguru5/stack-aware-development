# Go web: net/http, Gin, Echo, Fiber, Chi

## Contents
- Inspect the application
- Framework notes
- Handler conventions
- Pitfalls
- Security
- Performance
- Testing

## Inspect the application

- Router from `go.mod` and `main.go`/`cmd/<app>/main.go`: Gin, Echo, Fiber, Chi, gorilla/mux, or the standard library `http.ServeMux` (method and path-parameter patterns depend on the Go version).
- Layout: `internal/handler` (or `api`, `http`, `transport`), `internal/service`, `internal/repository`/`store`, or packages per domain. Wiring in `main` (manual DI) or wire/fx.
- Data access: pgx, `database/sql` + sqlx, sqlc-generated queries, GORM, ent, Bun. Migrations: golang-migrate, goose, Atlas, or others.
- Shared response helpers (`respondJSON`, `writeError`), error types, middleware (auth, logging, request ID, recovery).

## Framework notes

- **Gin**: `*gin.Context`. Binding with `ShouldBindJSON`/`ShouldBindQuery` plus `binding:` struct tags (validator). Abort with `c.AbortWithStatusJSON`. Route groups for versioning and auth.
- **Echo**: handlers return `error`. A centralized `HTTPErrorHandler` and `echo.NewHTTPError`. Binding plus a registered validator.
- **Fiber**: built on fasthttp, not `net/http`. Its `*fiber.Ctx` values must not be retained after the handler returns (copy strings or bytes), and many `net/http` middlewares aren't compatible.
- **Chi / net/http**: standard `http.Handler`/`http.HandlerFunc`, middleware as `func(http.Handler) http.Handler`, URL params via `chi.URLParam` or `r.PathValue` (newer stdlib). Decode JSON with `json.NewDecoder` and `DisallowUnknownFields` if the project does.

## Handler conventions

- Handlers stay thin: parse and validate → call the service → map the result or error to a response, using the existing helpers and error mapping.
- Pass `r.Context()` (or `c.Request.Context()`) down to services and DB calls.
- Query parameters (pagination, filters): parse with explicit defaults and bounds. Return 400 with the existing error shape on invalid input.
- Keep the response envelope consistent with the other handlers (bare JSON vs `{data, meta}`, field naming via `json:` tags).

## Pitfalls

- Introducing a second router or framework, or an ORM, next to existing pgx/sqlc code.
- Leaking goroutines from handlers. Ignoring context cancellation.
- Forgetting `defer rows.Close()` or `rows.Err()`. Shadowed `err` variables.
- Writing headers after the body has started. Calling the next handler after writing an error response.

## Security

- Auth middleware on the correct route group. Get the principal from the context with the project's typed key or accessor.
- Validate and bound all inputs. Limit request body size (`http.MaxBytesReader` or the framework equivalent).
- Use placeholders in SQL. With dynamic sorting, map allowed field names to fixed column names.
- Set server timeouts (`ReadHeaderTimeout` etc.) if you're creating the server, and match existing config.

## Performance

- Paginate in SQL (keyset or `LIMIT/OFFSET` per convention) with a deterministic `ORDER BY`. Add an index if needed.
- Avoid per-request allocation-heavy work in hot paths only when profiling shows it matters (`pprof` if the project exposes it).
- Reuse `http.Client` and DB pools. Set timeouts on outbound calls.

## Testing

- `httptest.NewRecorder` + `router.ServeHTTP(w, req)` for handler tests (Gin/Echo/Chi). Fiber uses `app.Test(req)`.
- Table-driven tests for parameter validation (missing, invalid, zero, negative, over the max). Mock the service layer via interfaces as neighbors do, or use a real DB in integration tests guarded by build tags or env.
