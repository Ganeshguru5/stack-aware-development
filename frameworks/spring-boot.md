# Spring Boot

## Contents
- Inspect the application
- Common architecture
- Validation and errors
- Persistence
- Security
- Configuration
- Pitfalls
- Performance
- Testing

## Inspect the application

- Spring Boot version (parent POM, BOM, or plugin version). Boot 3+ uses `jakarta.*`. Boot 2 uses `javax.*`. Never mix them.
- Starters present: `web` (MVC, servlet) vs `webflux` (reactive), `data-jpa`/`data-jdbc`/`data-mongodb`/`data-redis`, `security`, `validation`, `actuator`, `oauth2-resource-server`.
- Main class package. Component scanning covers that package and its sub-packages only, so new components must live underneath it.
- `application.yml`/`.properties`, profiles (`application-<profile>.yml`), `@ConfigurationProperties` classes.
- Global handlers (`@RestControllerAdvice`), security config (`SecurityFilterChain` beans), mappers (MapStruct, manual), Lombok usage, migration tool (Flyway/Liquibase).

## Common architecture

- `@RestController` → `@Service` → `Repository` (Spring Data interface or custom), with DTOs (often records) at the API boundary. Some projects use package-by-feature or hexagonal modules. Follow the existing one.
- Constructor injection. Business logic in services, not controllers. Transactions on service methods (`@Transactional`), read-only where the project marks them.

## Validation and errors

- Bean Validation annotations on request DTOs (`@NotBlank`, `@Email`, `@Size`) with `@Valid` on the controller parameter. Use groups or custom validators if the project has them.
- Map exceptions in the existing `@RestControllerAdvice`, using its response shape (custom envelope or `ProblemDetail`). Add a handler there for new exception types instead of building responses in controllers.
- Uniqueness (for example a duplicate email): check in the service for a friendly error **and** rely on a unique constraint. Translate `DataIntegrityViolationException` to 409 the way the project does.

## Persistence

- Spring Data JPA: derived queries, `@Query` (JPQL or native), specifications, or Querydsl. Copy the neighbor.
- Avoid N+1: `JOIN FETCH`, `@EntityGraph`, or DTO projections for read endpoints. Keep `open-in-view` behavior in mind. If it's disabled, lazy loading outside transactions fails.
- `@Transactional` works through proxies: self-invocation and private methods bypass it. Rollback defaults to unchecked exceptions only.
- Pagination: `Pageable`/`Page`/`Slice` if the project uses them. Check the response shape the API exposes (a raw `Page` serialization vs a custom DTO).
- Schema changes go through Flyway/Liquibase migrations. Don't rely on `ddl-auto` for anything except what the project already does.

## Security

- Spring Security filter chain: put new endpoints under the correct matcher rules, which are evaluated in order. Method security (`@PreAuthorize`) if enabled.
- Get the current user from `SecurityContext`/`@AuthenticationPrincipal`, as existing code does.
- Password hashing via the configured `PasswordEncoder`. Never store raw passwords.
- CSRF is enabled by default for session-based apps. Stateless token APIs often disable it, so understand why before changing it.
- Don't expose actuator endpoints beyond what's configured.

## Configuration

- Typed `@ConfigurationProperties` over scattered `@Value` if the project uses them. Secrets come from env or a secret store with placeholders in YAML.
- Profile-specific overrides. Don't put production values in the default profile.

## Pitfalls

- Mixing WebFlux and blocking JDBC/JPA on event-loop threads.
- Returning JPA entities directly (lazy-loading serialization issues, leaked fields, infinite recursion on bidirectional relations).
- Field injection in new code when the project uses constructor injection.
- Adding Node/Express-style middleware concepts. Spring uses filters, interceptors, and advice.
- Introducing a second mapping or validation library.

## Performance

- Use SQL logging (`spring.jpa.show-sql` or Hibernate statistics, in tests or locally) to count queries.
- Fetch-size and batch settings for bulk operations. Use pagination for lists.
- Caching through Spring Cache abstraction if already configured.
- Watch the HikariCP pool size relative to thread count and DB limits.

## Testing

- Slice tests: `@WebMvcTest` with `MockMvc` (mock the services, using the project's mock-bean annotation for the Boot version), `@DataJpaTest` for repositories. Full `@SpringBootTest` for integration, often with Testcontainers.
- Use JUnit 5 + Mockito + AssertJ if those are present. Use `spring-security-test` helpers (`@WithMockUser`, `jwt()` post-processors) for secured endpoints.
- Test validation failures (400), conflicts (409), not found (404), and auth (401/403) along with the happy path.
