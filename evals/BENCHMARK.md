# Benchmark: with vs. without the skill

The first baseline comparison, run on 2026-10-08. It's a small, single-model, single-run study. Read it as a sanity check, not a measurement of effect size.

## Method

- **Fixtures:** 12 repositories, one per case in `evals.json`, stored in `fixtures.json`. Rebuild them with `python evals/build_fixtures.py unpack <dir>`. Each one plants the situation the case tests: an existing Auth.js setup, an N+1 query, a missing `asyncHandler`, a populated table, a PR with redundant libraries, and so on. None of them contains comments that hint at the expected answer.
- **Runs:** 24 runs, one with the skill and one without for each case. Every run used a fresh agent on the same model (Claude Opus 5.5) with the same prompt and rules. The skill run was told to read `SKILL.md` first, which forces activation, so these results don't test triggering. Neither condition had build tools, dependencies, databases or network access. No run could execute tests, and every agent said so.
- **Grading:** 12 grader agents, one per case. Each grader saw both runs labelled A/B in random order and wasn't told which run used the skill. Graders inspected the git diffs themselves and scored each expectation as PASS (1), PARTIAL (0.5) or FAIL (0), and each failure condition as triggered or not.

## Results

| # | Case | With skill | Without | Grader's comparison |
|---|------|-----------|---------|---------------------|
| 1 | Java/Spring: create user | 8/8 | 8/8 | Equivalent |
| 2 | Next.js: "add authentication" | 8/8 | 7.5/8 | Mixed: with-skill asked before changing the schema; without-skill fixed the adapter schema unasked but delivered a more working setup |
| 3 | FastAPI: slow endpoint | 8/8 | 7.5/8 | With-skill slightly better: it measured query counts before and after (22 → 2 on SQLite) |
| 4 | Go/Gin: pagination | 7.5/8 | 7.5/8 | Equivalent; near-identical code, and neither added httptest handler tests |
| 5 | Clojure (no dedicated guidance) | 5.5/6 | 4.5/6 | With-skill better: the without-skill test inserted NULL into a NOT NULL column, and its test helper drifted from the HoneySQL convention |
| 6 | Express: intermittent crash | 5.5/6 | 5.5/6 | With-skill slightly better on process: took the version from the lockfile and checked the sibling routes |
| 7 | .NET: required column on populated table | 6/6 | 6/6 | With-skill slightly better: its EF model default matched the migration, and it tested legacy rows |
| 8 | Kotlin: PR review | 6/6 | 5.5/6 | With-skill slightly better: explicit stack profile and deeper reasoning on the second ORM |
| 9 | Monorepo: billing endpoint | 5/5 | 5/5 | Equivalent; both scoped correctly to the package |
| 10 | Trivial typo | 3/3 | 3/3 | Equivalent; byte-identical diffs, so the skill added no ceremony |
| 11 | Django: owner-only edits | 7/7 | 7/7 | **Without-skill** slightly better: it tested more denial paths |
| 12 | Drizzle + PostgreSQL skill | 5/5 | 4.5/5 | With-skill slightly better: correct drizzle-kit snapshot naming and `IF NOT EXISTS` |
| | **Total** | **74.5/76 (98.0%)** | **71.5/76 (94.1%)** | With 6 · without 1 · equivalent or mixed 5 |

Failure conditions triggered: **0 with the skill, 0 without.**

## Interpretation

- **The effect is small and not significant.** A 3-point difference over 12 single runs is within run-to-run variance. Most "with-skill better" calls were "slightly".
- **The baseline was strong because the fixtures are clean.** Every fixture had an obvious existing feature to copy. A strong model finds that feature without help, which is the behaviour the skill teaches. None of the planted traps (wrong package manager, a second ORM, a new auth library) caught the baseline.
- **Where the skill seemed to help:** on the stack it had no dedicated guidance for (case 5), on measurement and verification habits (cases 3 and 6), and on migration and tooling consistency (cases 7 and 12). Its reports were also more consistently structured (stack, pattern followed, deviations), which graders sometimes credited.
- **No sign of harm.** It added no ceremony to the trivial change (case 10) and didn't over-engineer elsewhere.

## Limitations and next steps

- One model and one run per case. Repeat each case 3–5 times, and include smaller or faster models, where the skill is more likely to matter.
- The fixtures are tidy. Messier repositories should show the effect better: conflicting conventions, stale READMEs that name the wrong framework, dead dependencies, half-finished migrations.
- Triggering wasn't tested. Use `trigger-evals.json` in a real agent harness.
- No run could execute tests. A run with real toolchains would also grade compile and test results.
- Graders could sometimes infer the condition from report structure. Blinding was partial.
