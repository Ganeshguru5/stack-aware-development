# C# / .NET

## Contents
- Detect
- Project structure
- Dependency injection
- async/await
- Exceptions and errors
- Configuration
- Data access
- Testing
- Verification commands

## Detect

- Target framework from `<TargetFramework(s)>` in `.csproj`. SDK pin from `global.json`. Language version from `<LangVersion>` (or the default for the target). Nullable reference types from `<Nullable>enable</Nullable>`. Check `Directory.Build.props` for shared settings.
- Web: ASP.NET Core ([dotnet](../frameworks/dotnet.md)), with controllers vs minimal APIs, Blazor, or Razor Pages. Also check for worker services, Azure Functions, desktop (WPF/WinForms/MAUI), or class libraries.
- Package versions may be centralized in `Directory.Packages.props` (central package management). If so, add versions there, not in the project file.

## Project structure

- Solutions often split into projects by layer (`Api`, `Application`, `Domain`, `Infrastructure`) or by feature. Respect project references. Don't add a reference that inverts the dependency direction (for example Domain → Infrastructure).
- File-scoped namespaces, `record` types, primary constructors, collection expressions: use them only if the language version and the codebase allow them.
- Follow `.editorconfig` and analyzer rules. Warnings-as-errors may be enabled.

## Dependency injection

- Register services the way the project does (in `Program.cs`, extension methods like `AddXyz(this IServiceCollection ...)`, or assembly scanning).
- Choose lifetimes correctly: `DbContext` is scoped, and a singleton must not capture scoped services. Match the lifetimes of similar existing services.
- Use constructor injection. Don't use the service locator (`IServiceProvider.GetService`) in business code.
- Typed `HttpClient` via `IHttpClientFactory`, never `new HttpClient()` per call.

## async/await

- Async all the way: no `.Result`, `.Wait()`, or `GetAwaiter().GetResult()` on request paths. These cause thread starvation and deadlocks.
- Pass `CancellationToken` through to EF Core and HTTP calls if the codebase does.
- Avoid `async void` except for event handlers. Follow the project's convention on `ConfigureAwait(false)` (common in libraries, usually unnecessary in ASP.NET Core apps).

## Exceptions and errors

- Use the project's exception types and the global handler (exception-handling middleware, `IExceptionHandler`, ProblemDetails configuration), or its Result-pattern types if they're used.
- Don't catch `Exception` broadly without rethrowing or handling it. Use `throw;` (not `throw ex;`) to preserve stack traces.
- With nullable reference types enabled, respect the annotations, and avoid `!` suppression unless it's justified.

## Configuration

- `appsettings.json` plus environment-specific files, env vars, user secrets in development, and a vault/secret store in production. Bind to typed options (`IOptions<T>`) if the project does.
- Never commit secrets to `appsettings*.json`.

## Data access

- EF Core: use the existing `DbContext`, configuration style (data annotations vs Fluent API `IEntityTypeConfiguration`), and migration workflow (`dotnet ef migrations add`). Watch for N+1 (`Include`, projections with `Select`), use `AsNoTracking` for reads where the project does, and keep queries server-evaluated.
- Dapper/ADO.NET: parameterized queries only.

## Testing

- xUnit, NUnit, or MSTest: match the existing test projects (`*.Tests`, `*.IntegrationTests`). Mocking with Moq or NSubstitute, assertions with the library already used.
- Integration tests for APIs often use `WebApplicationFactory<Program>`. Follow how neighbors replace services and databases (Testcontainers, SQLite in-memory, or a test database).

## Verification commands

`dotnet build`, `dotnet test` (filter with `--filter "FullyQualifiedName~Name"`), `dotnet format --verify-no-changes` if CI uses it. Run against the specific project or solution file in multi-project repos.
