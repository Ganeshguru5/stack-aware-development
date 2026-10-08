# Other languages and unrecognized stacks

## Contents
- Be honest about coverage
- General procedure
- Brief notes: PHP, Ruby, Elixir, Swift/Kotlin mobile, Dart/Flutter, Scala, C/C++
- What not to do

## Be honest about coverage

This skill has no dedicated guidance for this stack. Say so in the stack profile ("no dedicated guidance; following repository evidence"). Rely on:
1. The repository itself: code, tests, configs, docs, CI.
2. Specialized skills or documentation tools available in the environment for this technology.
3. General engineering principles from the cross-cutting references.

Never fill gaps with idioms from a different, more familiar framework.

## General procedure

1. **Toolchain**: find the manifest, lockfile, and build tool. Find the version pins.
2. **Entry points**: where execution starts, and how routes, commands, and handlers are registered.
3. **Nearest neighbor**: find the most similar existing feature and copy its structure exactly, including tests.
4. **Commands**: get build, test, and lint commands from CI config, the Makefile, or the README. Don't invent them.
5. **Dependencies**: only add a dependency when nothing in the project covers the need. Use the ecosystem's package manager so the lockfile updates.
6. **Verify**: run the project's tests and checks. If you can't, report it.
7. **Flag uncertainty**: in the report, point out any framework-specific behavior you relied on but couldn't confirm from the codebase.

## Brief notes

**PHP**: Composer (`composer require`, autoload via PSR-4 in `composer.json`). Laravel: Eloquent models, migrations (`php artisan make:migration`), Form Requests for validation, policies/gates for authorization, Pest or PHPUnit. Symfony: Doctrine entities and migrations, services autowired via `config/services.yaml`, Validator constraints, Voters for authorization. Watch for N+1 queries (use eager loading such as `with()`) and mass assignment (`$fillable`/`$guarded`). Check `declare(strict_types=1)` usage and static analysis (PHPStan/Psalm) levels.

**Ruby**: Bundler (`bundle add`, `bundle exec`). Rails: follow its conventions (fat models or service objects, whichever is used), generators for migrations, strong parameters, ActiveRecord validations plus DB constraints, `includes` for N+1, RSpec or Minitest (match the existing suite), and RuboCop config. Sinatra/Hanami: follow the app's own structure.

**Elixir**: Mix, Phoenix contexts as boundaries, Ecto changesets for validation, Ecto migrations, ExUnit, `{:ok, _}`/`{:error, _}` tuples. Let supervisors handle crashes the way the codebase does.

**Swift / Kotlin (mobile)**: Swift Package Manager or CocoaPods; Gradle for Android. Follow the existing architecture (MVVM, TCA, MVI), UI framework (SwiftUI vs UIKit, Compose vs Views), concurrency model (async/await, Combine, coroutines/Flow), and DI. Keep main-thread/UI-thread rules.

**Dart / Flutter**: `pubspec.yaml`. Follow the existing state-management approach (Provider, Riverpod, Bloc, etc.). Don't add a second one. Test with `flutter test`.

**Scala**: sbt or Mill. Check the effect system (Cats Effect, ZIO, Futures) and follow it consistently. Don't mix effect systems.

**C / C++**: CMake/Meson/Make/Bazel. Respect the language standard version, the existing memory-management conventions (RAII, smart pointers, ownership rules), error style (exceptions vs error codes), and sanitizer/warning flags in CI.

## What not to do

- Pretend to know framework specifics you can't confirm from the code or available documentation.
- Restructure the project to look like a stack you know better.
- Introduce a build tool, test framework, or package manager the project doesn't use.
