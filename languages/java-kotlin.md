# Java / Kotlin (JVM)

## Contents
- Detect
- Build tools
- Dependency injection and structure
- Exceptions and errors
- Concurrency
- Data access
- Configuration
- Kotlin specifics
- Testing
- Verification commands

## Detect

- Java version: `<java.version>`/`maven.compiler.release`, Gradle `toolchain { languageVersion }`, `.java-version`, `.sdkmanrc`, the Dockerfile base image. The language level determines which features are allowed (records, sealed types, pattern matching, virtual threads, text blocks). Don't use features above the configured level.
- Framework: Spring Boot ([spring-boot](../frameworks/spring-boot.md)), Quarkus, Micronaut, Jakarta EE, Ktor, Dropwizard, or plain Java. Check `javax.*` vs `jakarta.*` imports. They aren't interchangeable, so match what the project uses.
- Kotlin: `.kt` sources, `kotlin("jvm")` plugin, `src/main/kotlin`.

## Build tools

- Use the wrapper (`./mvnw`, `./gradlew`) if it exists, so the project's pinned version is used.
- Maven: add dependencies in the right module's `pom.xml`. Versions often come from a parent POM or BOM (`dependencyManagement`), so omit versions when they're managed.
- Gradle: follow the existing DSL (Groovy vs Kotlin), version catalog (`libs.versions.toml`), convention plugins (`buildSrc`, `build-logic`), and configuration names (`implementation`, `testImplementation`).
- Multi-module builds: put code in the module that owns the concern, and respect inter-module dependencies.

## Dependency injection and structure

- Constructor injection with `final` fields, as most modern codebases do. Follow the existing style, including Lombok (`@RequiredArgsConstructor`) if it's used.
- Package-by-layer (`controller`, `service`, `repository`) vs package-by-feature: match it.
- DTOs vs entities: if the codebase maps entities to DTOs (manually, with MapStruct, or with records), do the same. Don't expose entities from controllers if the project doesn't.
- Lombok, records, and immutability: follow what's used. Don't introduce Lombok into a project without it.

## Exceptions and errors

- Use the project's exception hierarchy (domain exceptions, `ResponseStatusException`, custom error codes) and the global handler.
- Don't catch `Exception` broadly and swallow it. Don't log and rethrow the same exception at every layer. Preserve the cause when wrapping.
- Checked vs unchecked: follow the codebase. Most Spring codebases use unchecked domain exceptions.
- Null handling: follow the project's approach (`Optional` returns from repositories, nullability annotations, Kotlin null safety). Don't return `null` collections.

## Concurrency

- Most request handling is thread-per-request. Shared mutable state in singletons (beans, services) must be thread-safe or avoided.
- Use the project's executors and async mechanisms (`@Async` with a configured executor, `CompletableFuture`, virtual threads if enabled, Kotlin coroutines, reactive types). Don't create raw threads or unbounded pools.
- Reactive stacks (WebFlux, Mutiny, Reactor): never block (JDBC, `Thread.sleep`, `.block()`) on event-loop threads.
- Transactions and thread-locals don't propagate automatically to other threads.

## Data access

- JPA/Hibernate: watch lazy loading (N+1, `LazyInitializationException` outside transactions), use fetch joins or entity graphs for read paths, avoid `EAGER` as a blanket fix, and implement `equals`/`hashCode` on entities carefully. Derived-query method names vs `@Query`: follow the neighbors.
- JDBC/`JdbcTemplate`/jOOQ/MyBatis: use the existing approach. Parameterize, and don't concatenate SQL.
- Migrations: Flyway or Liquibase. Never edit applied migrations.

## Configuration

- Use the framework's config (`application.yml`/`.properties`, profiles, typed config properties classes). Don't read `System.getenv` scattered through code if the project binds config centrally.
- Secrets come from env or a secret manager, never committed config.

## Kotlin specifics

- Use idiomatic Kotlin in Kotlin modules (data classes, null safety, extension functions) consistent with the project's style. Don't write Java-style Kotlin, and don't convert Java files to Kotlin unasked.
- Coroutines: use the project's scopes and dispatchers. Don't use `GlobalScope`. Use `Dispatchers.IO` for blocking calls if coroutines are used.
- Kotlin with Spring/JPA needs the `kotlin-spring`/`kotlin-jpa` (all-open/no-arg) plugins. Check they're configured before adding entities.

## Testing

- JUnit 5 (`org.junit.jupiter`) vs JUnit 4: match the project. Mockito or MockK for mocks, AssertJ or Hamcrest for assertions, Testcontainers for real databases, whatever is already used.
- Test location: `src/test/java` or `src/test/kotlin`, mirroring the package. Integration tests may live in a separate source set or use a naming suffix (`*IT`) run by Failsafe.

## Verification commands

`./mvnw -q -pl <module> test` / `./mvnw verify`, or `./gradlew :<module>:test` / `./gradlew check`. Run a single test class with `-Dtest=ClassName` (Maven Surefire) or `--tests ClassName` (Gradle). Include static checks the build runs (Checkstyle, Spotless, ktlint, detekt, SpotBugs, Error Prone).
