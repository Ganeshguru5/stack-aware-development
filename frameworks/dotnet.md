# ASP.NET Core

## Contents
- Inspect the application
- Common architecture
- Validation and errors
- Data access
- Security
- Pitfalls
- Performance
- Testing

## Inspect the application

- Target framework and SDK (`.csproj`, `global.json`). Hosting model in `Program.cs` (`WebApplication.CreateBuilder`; older apps use `Startup.cs`).
- API style: **controllers** (`[ApiController]`, `Controllers/`) vs **minimal APIs** (`app.MapGet(...)`, often grouped with `MapGroup` or endpoint classes). Also Razor Pages, MVC views, Blazor, gRPC. Add to the style already used.
- Layering: single project, or Clean/Onion solution (`Api`/`Application`/`Domain`/`Infrastructure`), possibly with MediatR (commands/queries + handlers). If MediatR or a similar library is used, new features follow the same request/handler pattern.
- Cross-cutting: middleware pipeline order, exception handling, auth schemes, validation (FluentValidation vs DataAnnotations), mapping (AutoMapper, Mapster, manual), logging (built-in `ILogger`, Serilog).

## Common architecture

- Endpoint → (handler/service) → `DbContext` or repository. Many EF Core codebases use `DbContext` directly as the unit of work. Don't add a generic repository layer if the project doesn't have one.
- Register new services in the same place and style as existing ones, with correct lifetimes.
- Options pattern for config (`IOptions<T>`), bound from `appsettings` sections.

## Validation and errors

- `[ApiController]` returns automatic 400 ProblemDetails for model-validation failures. Minimal APIs need explicit validation (endpoint filters, FluentValidation, or the built-in mechanism of the installed version). Follow the project.
- Errors go through the existing exception handler or middleware and ProblemDetails configuration. Return typed results (`Results.NotFound()`, `TypedResults`, `ActionResult<T>`) consistent with neighbors.

## Data access

- EF Core: entity configuration style, migrations (`dotnet ef migrations add <Name>` in the right project with the right startup project), and the `DbContext` lifetime (scoped).
- Avoid N+1 with `Include`/`ThenInclude` or projections (`Select` into DTOs). Use `AsNoTracking` for read-only queries if neighbors do. Avoid client evaluation of large sets.
- Handle `DbUpdateConcurrencyException` (row versions) and unique-index violations as the project does.

## Security

- Authentication schemes (cookies, JWT bearer, OIDC) are configured in `Program.cs`. Protect endpoints with `[Authorize]`/`RequireAuthorization()` and policies, the same way as neighbors. Check whether a fallback policy (authorize by default) is configured.
- Anti-forgery for cookie-authenticated form posts (MVC/Razor Pages/Blazor forms).
- Secrets in user-secrets (dev) or a vault (prod), never in `appsettings.json`.
- CORS policies registered by name. Use the existing policy.

## Pitfalls

- Blocking on async (`.Result`, `.Wait()`), and `async void`.
- Capturing a scoped service (`DbContext`) in a singleton or background service. Create a scope instead (`IServiceScopeFactory`).
- Creating `HttpClient` instances manually.
- Mixing controllers and minimal APIs for the same resource without a reason.
- Middleware order mistakes (authentication before authorization, both before endpoints).

## Performance

- Async I/O end to end. Paginate. Project to DTOs.
- Output/response caching and `IMemoryCache`/`IDistributedCache` only if the project already uses them.
- Watch EF Core query logs (`LogTo` or logging category settings) for N+1 and unexpected queries.

## Testing

- xUnit/NUnit/MSTest, matching existing test projects. `WebApplicationFactory<Program>` for API integration tests, with `ConfigureTestServices` to replace dependencies. Test auth handlers if neighbors use them.
- Use the project's DB strategy: Testcontainers, a dedicated test DB, or SQLite in-memory (note provider differences).
