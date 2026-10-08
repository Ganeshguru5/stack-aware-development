# Security

## Contents
- Proportional review
- Checklist by risk
- Dependencies
- Secrets and logging
- Reporting

## Proportional review

Review the code the change touches, against the risks it actually introduces. Don't turn every task into a full audit.

| The change touches... | Check |
|-----------------------|-------|
| User input (params, bodies, headers, files) | Validation, injection, output encoding |
| Queries / data access | Injection, authorization scoping, mass assignment |
| Auth, sessions, permissions | [authentication.md](authentication.md), [authorization.md](authorization.md) |
| File upload/download/paths | Path traversal, type/size validation, storage location |
| Outbound requests from user-supplied URLs | SSRF |
| Cookies / browser-facing endpoints | CSRF, CORS, security headers, XSS |
| Deserialization of untrusted data | Unsafe deserializers |
| Secrets, config, logs | Exposure |
| Dependencies | Known vulnerabilities, provenance |

If you spot a serious issue outside the change, report it. Don't fix it silently unless it's in scope.

## Checklist by risk

- **Injection**: parameterized queries through the existing data-access layer. No string-built SQL, shell commands, LDAP or NoSQL filters, or template strings with input. Use argument arrays for subprocess calls, never a shell string. Allowlist dynamic identifiers.
- **XSS**: rely on the framework's auto-escaping. Treat every raw-HTML escape hatch (`dangerouslySetInnerHTML`, `v-html`, `|safe`, `Html.Raw`, `th:utext`) as a review point and sanitize with the project's sanitizer.
- **Broken access control**: object-level checks, tenant scoping, deny by default (see [authorization.md](authorization.md)).
- **Mass assignment**: bind input to DTOs/allowlists, not directly onto persistence entities.
- **File uploads**: enforce size limits, validate type by content and not just extension, generate server-side filenames, store outside the web root or in object storage, never execute uploaded content, and prevent path traversal (`../`) when building paths.
- **SSRF**: for user-influenced URLs, allowlist hosts/schemes, block internal/link-local/metadata addresses after DNS resolution, disable or limit redirects, set timeouts.
- **CSRF**: required when auth relies on cookies. Use the framework's CSRF protection and `SameSite` cookies. Bearer-token APIs that don't use cookies are generally not CSRF-prone.
- **CORS**: explicit allowed origins. Never reflect arbitrary origins together with credentials, and never use `*` with credentials. Follow the existing configuration location.
- **Deserialization**: never deserialize untrusted data with formats that can instantiate arbitrary types (native object serialization, pickle, unsafe YAML loaders, polymorphic JSON typing without allowlists).
- **Crypto**: use the platform's vetted libraries. Use secure random generators for tokens. No home-made schemes.
- **Rate limiting / resource exhaustion**: bound page sizes, payload sizes, regex complexity on untrusted input, and expensive operations. Use the existing rate limiter if there is one.
- **Error handling**: no stack traces or internal details in responses.

## Dependencies

- Add dependencies only when needed, from the ecosystem's official registry, using the project's package manager so the lockfile is updated.
- Check that the package name is correct (typosquatting) and that it's maintained.
- When updating dependencies, read the changelog for breaking and security notes, and run the project's audit tool if it has one (`npm audit`/`pnpm audit`, `pip-audit`, `mvn`/Gradle dependency-check plugins, `govulncheck`, `dotnet list package --vulnerable`, `cargo audit`), or the scanner CI uses.

## Secrets and logging

- Never hard-code secrets, keys, or credentials, including in tests and fixtures. Use the project's config mechanism and add placeholders to `.env.example`.
- Don't log passwords, tokens, session IDs, full payment data, or unnecessary personal data. Follow the existing redaction helpers.
- If you find a committed secret, tell the user. It needs rotation, and removing it from the code alone isn't enough.

## Reporting

In the final report, list security-relevant decisions (for example "the new endpoint requires the `orders:write` permission and scopes queries by tenant") and anything you couldn't verify.
