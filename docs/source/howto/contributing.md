# Contributing to kfactory

kfactory is an open-source project — contributions are welcome!

## Quick links

- [GitHub repository](https://github.com/gdsfactory/kfactory)
- [Issue tracker](https://github.com/gdsfactory/kfactory/issues)
- [Pull request template](https://github.com/gdsfactory/kfactory/blob/main/.github/PULL_REQUEST_TEMPLATE.md)

## Development setup

kfactory uses [uv](https://docs.astral.sh/uv/) for environment management and
[just](https://just.systems/) as a task runner.

```bash
# Clone the repository
git clone https://github.com/gdsfactory/kfactory.git
cd kfactory

# Set up the full development environment (installs all extras + pre-commit hooks)
just dev
```

`just dev` is equivalent to:

```bash
uv sync --all-extras
uv pip install -e . -U
uv run pre-commit install
```

## Running tests

```bash
# Full test suite (parallel, uses logical CPU count)
just test

# Minimum-dependency variant (checks nothing was accidentally removed)
just test-min

# With coverage report in the terminal
just dev-cov

# Single test file or test by name
uv run -p 3.14 --with . --extra ci --isolated pytest tests/test_kcell.py -s
```

Tests require the git submodules to be initialised (`just init-submodule` is run
automatically before `just test`).

## Building the docs

```bash
# Build once (outputs to docs/site/)
just docs

# Live-reload server (edit files, browser refreshes automatically)
just docs-serve

# Remove the build artefact
just docs-clean
```

Documentation pages in `docs/source/**/*.py` are **executed** during the build
(`mkdocs-jupyter`).  Any exception in a notebook stops the build.  Always run
`just docs` locally before opening a docs PR.

When writing a new doc page, follow the jupytext percent format used throughout
the repo — see `docs_overhaul/notes_build_system.md` in the repository for
templates and gotchas.

## Code quality

```bash
# Lint
just lint        # ruff check

# Format
just format      # ruff format

# Type check (daemon — fast on repeat runs)
just mypy

# Experimental faster type checker
just ty
```

Pre-commit runs `ruff check --fix` and `ruff format` automatically on every
`git commit` once `just dev` has been run.

## Contribution workflow

1. **Fork** the repository and create a feature branch from `main`.
2. Make your changes.  Add or update tests in `tests/` if touching library code.
3. Run `just test` and `just docs` (if you touched documentation).
4. Open a pull request against `main` with a short summary of *what* and *why*.

### PR guidelines

- Keep PRs focused — one logical change per PR is easier to review.
- Add a test for every new public function or behaviour change.
- Documentation notebooks are required for new features exposed to end users.
- The PR title is used by the release drafter; start it with a verb
  (*Add*, *Fix*, *Update*, *Remove*).

## Project layout

```
src/kfactory/          # library source
tests/                 # pytest tests
docs/
  source/              # documentation pages (Markdown + jupytext .py notebooks)
  mkdocs.yml           # navigation + plugin config
Justfile               # common dev commands
pyproject.toml         # package metadata + dependencies
```

## Dependency extras

| Extra | Purpose |
|-------|---------|
| `kfactory[dev]` | Full dev environment (CI + type stubs + pre-commit) |
| `kfactory[ci]` | Test dependencies (`pytest`, coverage, etc.) |
| `kfactory[docs]` | Documentation build (`mkdocs-material`, mkdocs-jupyter, etc.) |
| `kfactory[ipy]` | Jupyter / IPython display helpers (`kf.show`, `.plot()`) |

## Getting help

- Open a [GitHub issue](https://github.com/gdsfactory/kfactory/issues) for bugs
  or feature requests.
- For usage questions, the [How-To Guides](best_practices.py) and
  [FAQ](faq.md) are a good starting point.

## See Also

| Topic | Where |
|-------|-------|
| Frequently asked questions | [How-To: FAQ](faq.md) |
| Installation instructions | [Getting Started: Installation](../getting_started/installation.md) |
| Common pitfalls to avoid | [How-To: Best Practices](best_practices.py) |
