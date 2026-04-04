# Build System & Infrastructure Notes

## Build commands

```bash
# Build docs (uses uv isolated env with docs extras)
just docs                    # default python 3.14
just docs python_version=3.13

# Serve locally with hot-reload
just docs-serve

# Clean built site
just docs-clean

# What `just docs` actually runs:
uv run -p 3.14 --with . --extra docs --isolated mkdocs build -f docs/mkdocs.yml
```

## mkdocs-jupyter configuration

From `docs/mkdocs.yml`:

```yaml
plugins:
  - mkdocs-jupyter:
      include_source: true       # show source code
      include_requirejs: true
      execute: true              # notebooks are EXECUTED during build
      allow_errors: false        # build FAILS on any notebook error
      kernel_name: python3
      execute_ignore:
        - "source/*.py"          # root .py files (helpers) are skipped
      ignore: ["source/*.py"]    # root .py files not treated as notebooks
      remove_tag_config:
        remove_input_tags:
          - hide                 # cells tagged "hide" have input removed
        remove_output_tags:
          - hide                 # cells tagged "hide" have output removed
```

**Key implication:** Any `.py` file in a subdirectory of `source/` WILL be executed as a notebook. Only `source/*.py` (root level) is excluded.

## Jupytext percent format template

Every notebook `.py` file must start with:

```python
# ---
# jupyter:
#   jupytext:
#     custom_cell_magics: kql
#     formats: py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.16.2
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---
```

Cell markers:
- `# %% [markdown]` — markdown cell (narrative text)
- `# %%` — code cell (executed)
- Lines starting with `# ` inside markdown cells are rendered as markdown

## MkDocs plugins chain (execution order matters)

1. **gen-files** — runs `gen_diagrams.py` and `gen_ref_pages.py` to create API ref pages
2. **mkdocstrings** — extracts docstrings for API reference (Google style)
3. **mkdocs-video** — embeds .webm videos
4. **search** — full-text search index
5. **mkdocs-jupyter** — converts and executes .py notebooks
6. **literate-nav** — reads SUMMARY.md for API reference nav
7. **section-index** — directory index pages
8. **markdown-exec** — runs code blocks in .md files

## Markdown extensions available

- `admonition` — note/warning/tip boxes
- `pymdownx.superfences` — fenced code blocks
- `pymdownx.tasklist` — checkboxes
- `pymdownx.tabbed` — tabbed content (useful for dbu/um examples)
- `pymdownx.emoji` — emoji shortcodes
- `pymdownx.snippets` — include file content with `--8<--`

## Theme: Material for MkDocs

- Dark/light mode toggle
- Sticky navigation tabs
- Custom `overrides/main.html` — adds download button for notebooks

## Docs dependencies (from pyproject.toml `[project.optional-dependencies] docs`)

```
kfactory[ipy]
erdantic>=1.1.1
markdown-exec>=1.10.3
mkdocs>=1.6.1
mkdocs-gen-files>=0.5.0
mkdocs-jupyter>=0.25.1
mkdocs-literate-nav>=0.6.2
mkdocs-material>=9.6.9
mkdocs-section-index>=0.3.9
mkdocs-video>=1.5.0
mkdocstrings[python]>=0.29.0
pymdown-extensions>=10.14.3
griffe-pydantic>=1.1.4
griffe-inherited-docstrings>=1.1.1
griffe-warnings-deprecated>=1.1.0
ruff>=0.9.2
```

## CI workflows

- `.github/workflows/docs.yml` — tests docs build on PRs + pushes to main + bi-daily cron
- `.github/workflows/pages.yml` — deploys to GitHub Pages on version tags (gh-pages branch)

## Things to watch out for

1. **Notebooks must be self-contained.** Each `.py` file executes in its own kernel. Define `LayerInfos` and imports in every notebook.
2. **`allow_errors: false`** means any exception kills the build. Test locally before committing.
3. **Cell naming collisions.** If two notebooks create a `@cell` function with the same name + params, they won't collide (separate kernels), but be aware within a single notebook.
4. **The `ignore` pattern** `source/*.py` uses glob, not regex. It only matches root-level `.py` files, not subdirectories. New `.py` files in `source/concepts/`, `source/routing/`, etc. WILL be processed.
5. **`--8<--` snippet inclusion** requires `check_paths: true`. Paths are relative to the docs source directory.
6. **Watch path** `../src/kfactory` means editing source code triggers hot-reload during `docs-serve`.
7. **Root .py helper files** (`complex_cell.py`, `layers.py`, `star.py`, `straight.py`) are in `docs/source/` and are excluded from notebook processing. They're imported/included by other docs via `--8<--`. If we move them, update snippet references.
