# Rust

## Contents
- Detect
- Dependencies and features
- Errors
- Async
- Ownership and API style
- Testing
- Verification commands

## Detect

- Edition (`edition` in `Cargo.toml`), toolchain (`rust-toolchain.toml`), MSRV (`rust-version`). Don't use features newer than the MSRV.
- Workspace (`[workspace]` members) vs single crate. Binary vs library crates.
- Web/async stack: Axum, Actix Web, Rocket, Warp, or Tonic (gRPC), on the Tokio or async-std runtime. Data access: SQLx (compile-time checked queries may need `DATABASE_URL` or offline `.sqlx` data), Diesel, SeaORM.

## Dependencies and features

- Add crates with `cargo add` in the correct workspace member. Use `[workspace.dependencies]` if the workspace centralizes versions.
- Enable only the needed features. Check existing feature flags before enabling new ones (for example TLS backend choices, which must stay consistent across crates).
- Check for an existing crate covering the need (serde, an error crate, tracing, an HTTP client) before adding another.

## Errors

- Follow the existing error strategy: typically `thiserror` enums for library/domain errors and `anyhow`/`eyre` for application-level errors. Use `?` for propagation and add context the way neighbors do.
- No `unwrap()`/`expect()` on fallible operations in request or library code, unless the codebase has a clear invariant convention (for example `expect` with a justification message).
- Map errors to HTTP responses through the framework's mechanism used in the project (for example an `IntoResponse` impl for the app error type).

## Async

- Don't block the async runtime: use async I/O, and move blocking or CPU-heavy work to `spawn_blocking` or equivalent.
- Don't hold a `std::sync::Mutex` guard across `.await`. Use the pattern the project uses (scoped locks or an async mutex).
- Spawned tasks need an ownership/shutdown story. Follow existing task management.

## Ownership and API style

- Follow the existing conventions for borrowing vs cloning, `Arc` for shared state (for example application state in web frameworks), and builder patterns.
- Keep `unsafe` out unless the project already uses it for the same reason, and document invariants if you must use it.
- Public API changes in library crates are semver-relevant. Flag breaking changes.

## Testing

- Unit tests in `#[cfg(test)] mod tests` beside the code, integration tests in `tests/`, doc tests in docs. Async tests use the runtime's test macro (for example `#[tokio::test]`).
- Use the existing test helpers. Database tests may use SQLx test fixtures or a test container. Follow the neighbors.

## Verification commands

`cargo build`, `cargo test -p <crate>` (or `cargo nextest run` if used), `cargo clippy --all-targets -- -D warnings` if CI does, and `cargo fmt --check`.
