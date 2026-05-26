# Repository Guidelines

## Project Structure & Module Organization

This repository is currently minimal and does not yet expose a formal source tree. As the project grows, keep production code under a dedicated source directory such as `src/`, tests under `tests/`, and reusable media or fixtures under `assets/` or `fixtures/`.

Suggested layout:

```text
src/        Application code
tests/      Automated tests
assets/     Static media, sample audio, or subtitle fixtures
docs/       Design notes and user-facing documentation
```

Keep generated artifacts, local caches, and large temporary files out of version control unless they are required test fixtures.

## Build, Test, and Development Commands

No project-specific build or test commands are defined yet. When tooling is added, document the canonical commands here and prefer scripts that work from the repository root.

Examples to add when applicable:

```bash
npm install        # Install JavaScript dependencies
npm test           # Run the test suite
npm run build      # Build production artifacts
python -m pytest   # Run Python tests
```

Avoid requiring contributors to memorize long commands; wrap common workflows in `package.json`, `Makefile`, or task runner scripts.

## Coding Style & Naming Conventions

Follow the conventions of the language and framework introduced into the repository. Use consistent indentation across each file type, descriptive names, and small modules with clear responsibilities.

Recommended patterns:

- Use `camelCase` for JavaScript/TypeScript variables and functions.
- Use `PascalCase` for classes, React components, and exported types.
- Use `snake_case` for Python functions, variables, and test files.
- Name subtitle, audio, and fixture files descriptively, for example `interview_sample.en.srt`.

Add formatters or linters early, such as Prettier, ESLint, Ruff, Black, or equivalent project tooling.

## Testing Guidelines

Place automated tests in `tests/` or beside source files using the project’s framework convention. Test names should describe the behavior under test, not implementation details.

Use representative fixtures for audio, transcripts, and subtitle output. Keep fixture files small enough for fast local test runs. Cover parsing, timestamp handling, encoding, and error paths once those features exist.

## Commit & Pull Request Guidelines

This directory is not currently a Git repository, so no existing commit convention is available. Use short, imperative commit messages such as:

```text
Add subtitle timestamp parser
Fix UTF-8 output handling
```

Pull requests should include a concise summary, test results, and any relevant before/after examples. For user-visible changes, include sample input and output. Link related issues when available.

## Agent-Specific Instructions

Before editing, inspect the current tree and preserve unrelated user changes. Keep changes scoped, document new commands in this file, and verify behavior with the smallest relevant test or manual check.
