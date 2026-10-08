# Node.js backends: Express, Fastify, NestJS

## Contents
- Inspect the application
- Express
- Fastify
- NestJS
- Cross-framework pitfalls
- Security
- Performance
- Testing

## Inspect the application

- Framework and major version from the lockfile. Express 4 and 5 differ in async error handling. Check which is installed.
- App bootstrap (`app.ts`, `server.ts`, `main.ts`): middleware/plugin order, body parsers, CORS, helmet/security headers, error handler, auth.
- Route organization: routers per resource, plugin folders, Nest modules.
- Validation library (Zod, Joi, Yup, class-validator, TypeBox/JSON Schema), ORM/driver, logger (pino, winston), config loader.

## Express

- Routes → (controllers) → services → data access. Follow the existing split.
- Register routes on the existing router for that resource. Mount new routers where the others are mounted.
- Error handling: errors must reach the error-handling middleware (`(err, req, res, next)`). In Express 4, rejected promises in async handlers are **not** caught automatically, so the project probably uses a wrapper (`asyncHandler`) or a patch library. Use the same one. Express 5 forwards rejected promises.
- Middleware order matters: auth before the route, error handler last.

## Fastify

- Encapsulation: plugins have their own scope. Decorators and hooks registered inside a plugin aren't visible to siblings unless wrapped with `fastify-plugin`. Register new routes in the right plugin.
- Use JSON Schema (or TypeBox/Zod type providers if configured) for `schema.body/querystring/params/response`. Response schemas also control serialization, so missing fields in the schema are dropped from responses.
- Use hooks (`onRequest`, `preHandler`) for auth, as existing routes do. Async handlers return values. Don't mix `reply.send` and `return` incorrectly.

## NestJS

- Module → controller → service (provider) → repository. New features usually get a module that's registered in the parent module. Follow the CLI-generated structure the project uses.
- DTOs with class-validator/class-transformer plus a global `ValidationPipe` (check `whitelist`/`forbidNonWhitelisted` options), or Zod pipes, whichever exists.
- Use guards for auth/roles (`@UseGuards`, custom decorators), interceptors for cross-cutting concerns, exception filters for error mapping. Reuse the existing ones.
- DI: provide services in the module that owns them. Export them to share. Avoid circular module imports (`forwardRef` is a smell, not a fix).

## Cross-framework pitfalls

- Mixing frameworks' idioms (Nest decorators in Express code, Express `req/res` in Nest controllers beyond what the project does).
- Unhandled promise rejections. Blocking the event loop with sync crypto or file I/O or with large JSON processing in a request.
- Creating DB clients or pools per request.
- Reading `process.env` everywhere instead of using the config module.

## Security

- Validate body, query, and params on every route. Limit body sizes.
- Use the existing auth middleware or guard. Never trust user IDs from the body.
- CORS configured with explicit origins. Security headers via the existing middleware.
- Parameterized queries. For MongoDB, sanitize filters against operator injection (`$gt` in user input).

## Performance

- Log with the project's async logger (pino is common), not `console.log` in hot paths.
- Stream large responses or files. Paginate lists. Watch ORM N+1 queries.
- For CPU-heavy work, offload to worker threads or queues the project already uses.

## Testing

- HTTP-level tests with the existing approach: Supertest against the app, `fastify.inject`, or Nest's `Test.createTestingModule` with `overrideProvider`.
- Unit tests for services with mocked repositories, following neighbors. Integration tests against a real DB if the project has them.
