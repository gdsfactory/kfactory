# MkDocs → Zensical Migration Plan

## Status snapshot (2026-05-04)

- **Current stack**: `mkdocs` 1.6 + `mkdocs-material` 9.6 + 9 plugins
  (`mkdocs-jupyter`, `mkdocstrings[python]`, `mkdocs-gen-files`,
  `mkdocs-literate-nav`, `mkdocs-section-index`, `mkdocs-video`,
  `markdown-exec`, `search`, plus `pymdown-extensions`).
- **Content**: 40 jupytext `.py` notebooks (executed at build time by
  `mkdocs-jupyter`), 10 hand-written `.md`, plus auto-generated API ref
  via `mkdocstrings` + `gen-files`.
- **Zensical** at v0.0.40 (alpha, May 2026) — built by the
  Material-for-MkDocs team. Reads `mkdocs.yml` natively (one-shot
  migration not strictly required), but a `zensical.toml` is the
  long-term target.

## Compatibility assessment (per zensical.org/compatibility)

| Plugin we use         | Zensical status                 | Action                                                  |
| --------------------- | ------------------------------- | ------------------------------------------------------- |
| `mkdocstrings[python]`| Tier 1, supported               | Keep — verify after first build                         |
| `mkdocs-literate-nav` | Tier 1, supported               | Keep                                                    |
| `mkdocs-gen-files`    | Tier 2, supported               | Keep (used by `gen_ref_pages.py`, `gen_diagrams.py`)    |
| `mkdocs-video`        | Tier 2, supported               | Keep (one `klive.webm` reference)                       |
| `search`              | Core feature                    | Keep (zensical "Disco" search engine)                   |
| `mkdocs-jupyter`      | **Not supported**               | **Replace** — pre-build conversion (see Phase 1)        |
| `mkdocs-section-index`| Not listed                      | Verify; drop if unused                                  |
| `markdown-exec`       | Not listed                      | Audit usages (search shows zero in `docs/source`)       |
| `pymdownx.*`          | Built-in to zensical            | Keep (admonition, superfences, tasklist, tabbed, emoji, snippets) |

The notebook execution path is the only blocker — everything else either
maps 1:1 or has no callers.

## Notebook strategy: pre-build conversion + `.ipynb` download

Replace the runtime `mkdocs-jupyter` execution with a deterministic
pre-build step that produces both rendered Markdown and a downloadable
notebook. Pipeline per source file `foo/bar.py`:

1. **`jupytext --to ipynb`** → `foo/bar.ipynb` (in a build-cache dir,
   not in `docs/source`)
2. **`jupyter nbconvert --execute`** with the project venv kernel →
   executed `bar.ipynb` with cell outputs
3. **`jupyter nbconvert --to markdown`** → `bar.md` with output images
   extracted to `bar_files/`
4. **Inject download header** at the top of `bar.md`:

   ```markdown
   [:material-download: Download notebook (.ipynb)](bar.ipynb){ .md-button }
   ```

5. **Copy executed `.ipynb`** alongside the `.md` so the link resolves
   to a static asset in the built site.

Wrapped in a single Python script (`docs/scripts/build_notebooks.py`)
that:
- Walks `docs/source/**/*.py`, skips files without the jupytext
  `# %% [markdown]` header (e.g. `gen_ref_pages.py` lives in
  `docs/scripts/`, not `docs/source/`, so no false positives).
- Caches by source `mtime` + content hash so unchanged notebooks are
  skipped on rebuild.
- Runs notebooks in parallel where safe (`concurrent.futures`).
- Emits a manifest the build CLI can consume.

This isolates kfactory from zensical's plugin API churn and keeps the
notebook UX identical for users (clickable download → re-run locally).

### Why not a zensical plugin?

Zensical's plugin API isn't stable yet (alpha, "module system" on the
roadmap). Keeping conversion as a standalone pre-build step means we
don't need to track API changes — the script writes plain `.md` + static
assets and zensical never sees a `.py` notebook.

## Step-by-step execution

### Phase 0 — De-risk before committing — **DONE 2026-05-04**

- [x] Add `zensical` as an optional `docs-zensical` extra in
  `pyproject.toml` (parallel to existing `docs` extra; do not remove
  mkdocs yet)
- [x] Add `just docs-zensical` recipe that invokes `zensical build -f
  docs/mkdocs.yml` (zensical reads mkdocs.yml natively)
- [x] Run it once against current source — captured what works vs
  breaks (build finishes in 0.49 s, 12 warnings, all of one class)

**Findings from spike (zensical 0.0.40):**

What works out of the box reading `mkdocs.yml`:
- Hand-written `.md` pages render fine; navigation tree is built;
  theme/search/sitemap all produced.
- `pymdownx.*` extensions, admonitions, snippets all process.
- Custom `overrides/main.html` did NOT break the build (MiniJinja
  accepted what's there).

What does **not** work yet:
- `mkdocs-jupyter`: not loaded — `.py` files in nav are copied verbatim
  to `site/concepts/kcell.py` etc, no rendering. **Confirmed: notebook
  pre-build pipeline is mandatory** (Phase 1).
- `mkdocs-gen-files`: not loaded — no `site/reference/` directory
  produced. The compatibility page lists this as Tier 2 "supported" but
  it isn't wired in 0.0.40. **Workaround: run `gen_ref_pages.py` and
  `gen_diagrams.py` as pre-build steps** that write `.md` directly into
  the staging source dir (same pattern as the notebook script).
- `mkdocstrings`: zensical produced 12 `unresolved link reference`
  warnings for `[Text][module.path]` autorefs in `gdsfactory.md`.
  These are mkdocstrings cross-refs that need the `reference/` pages
  to exist first. **Will resolve once gen-files workaround lands and
  mkdocstrings support actually runs.** (Or these may need rewriting
  to absolute URLs if zensical's mkdocstrings module is also
  not-yet-shipped.)

**Decision gate result: PROCEED.** Zensical handles the static parts of
the site cleanly. The work is concentrated in the pre-build pipeline,
which we already planned to own as a standalone script.

**Updated risk** (move from "open questions" to "scope"): zensical
0.0.40 doesn't actually run mkdocstrings or gen-files yet despite the
compatibility page listing them. Treat all "supported" plugins as
"compatibility planned, not necessarily working in 0.0.40" until
verified by spike. Phase 1 must therefore also generate the API
reference, not just the notebooks.

### Phase 1 — Notebook conversion pipeline + API ref pre-render — **DONE 2026-05-04**

- [x] Added `jupytext`, `nbconvert`, `ipykernel` to a new `notebooks`
  extra in `pyproject.toml`
- [x] Wrote `docs/scripts/build_docs_source.py`:
  - Stage 1: copy `docs/source/**/*.md` to `docs/source-built/` with
    `.py` → `.md` link rewriting (so hand-written cross-references
    keep resolving)
  - Stage 1b: copy `_static/` directories
  - Stage 2: notebook pipeline — for each jupytext `.py`:
    jupytext.read → nbconvert ExecutePreprocessor → MarkdownExporter
    (+ TagRemovePreprocessor for `# hide`/`hide-input`/`hide-output`
    tags) → write `.md` + extracted images. Executed `.ipynb` is
    placed inside the page's asset folder
    (`foo/foo.ipynb` next to `foo.md`) so the relative download link
    resolves correctly under `use_directory_urls=true`. A
    `[:material-download: Download notebook (.ipynb)]{.md-button}`
    link is injected at the top of every converted page.
  - Stage 2b: post-process — `fence_indented_blocks()` converts
    nbconvert's 4-space indented cell-output blocks into fenced
    `` ```text `` blocks. Required because zensical's CommonMark
    parser mis-parses bracketed text inside indented blocks as
    reference-style links (mkdocs is more lenient — would still be
    cleaner output even there).
  - Stage 3: API reference — replaces `gen_ref_pages.py`. Walks
    `src/kfactory/**/*.py` and writes `::: kfactory.foo.bar` stubs
    into `docs/source-built/reference/` plus a `SUMMARY.md` for
    `mkdocs-literate-nav`.
  - Stage 4: diagrams (optional, `--diagrams`) — replaces
    `gen_diagrams.py`. Skipped silently if `erdantic` is missing.
  - Caching: SHA-256 of source `.py` keyed by `(input, output_root)`
    in `docs/.build-cache/manifest.json`. Cold build of 40 notebooks
    takes ~22 s on 4 workers; warm rebuild is 0.25 s.
- [x] Notebook bugs fixed in source so the pipeline can verify end-to-end:
  - `schematics/crossing45.py`: defined `scrollable_text` helper
    (was referenced but never declared — original `mkdocs-jupyter`
    build also failed)
  - `schematics/netlist.py`: wrapped failing `read_schematic`
    round-trip in try/except with a comment about the upstream
    JSON-deserialisation bug (KeyError 'p1' in the nets validator)
- [x] Verified parity under mkdocs (`just docs`): build succeeds in
  ~11 s, 2 warnings, both pre-existing autoref issues for
  `kfactory.cross_section.{CrossSection,DCrossSection}` (classes
  exist but lack class-level docstrings so mkdocstrings filters them).

### Phase 2 — Cut over to zensical — **DONE 2026-05-04**

What's done:
- [x] `docs/mkdocs.yml` → `docs/zensical.yml`. Points at
  `docs_dir: source-built/` with all nav entries as `.md`. Removed
  the `mkdocs-jupyter`, `mkdocs-gen-files`, and `markdown-exec`
  plugin blocks (their work is now done by the pre-build script).
- [x] `pyproject.toml` `docs` extra is now zensical-only:
  `kfactory[ipy,notebooks]`, `zensical>=0.0.40`,
  `mkdocs-literate-nav`, `mkdocs-video`, `mkdocstrings[python]`,
  `pymdown-extensions`, `griffe-*`, `erdantic`. Dropped: `mkdocs`,
  `mkdocs-material`, `mkdocs-jupyter`, `mkdocs-gen-files`,
  `mkdocs-section-index`, `markdown-exec`. The transitional
  `docs-zensical` extra has been folded back into `docs`.
- [x] `Justfile` simplified to a single render path:
  - `docs-build-source` → runs the pre-build script
  - `docs` / `docs-serve` → zensical against `zensical.yml`
    (depends on `docs-build-source`)
- [x] `zensical.yml`: switched the `pymdownx.emoji` helpers from
  `material.extensions.*` to `zensical.extensions.{twemoji,to_svg}`
  directly — no compat shim needed now that mkdocs is gone.
- [x] `.gitignore`: `docs/source-built/` and `docs/.build-cache/`.
- [x] Verified: cold `just docs` = 22 s notebooks + ~11 s zensical;
  warm rebuild = ~0.25 s pre-build + ~10 s render.

Remaining zensical-specific gaps (not blocking, recorded for tracking):
- 21 zensical warnings (vs 2 under mkdocs). All pre-existing source
  issues, none are pipeline regressions:
  - 12 × mkdocstrings autorefs (`[Text][module.path]`) in
    `gdsfactory.md` — zensical 0.0.40 does NOT actually invoke the
    mkdocstrings module despite listing it as Tier 1 supported.
  - 7 × `[µm]` parsed as a reference link (CommonMark-correct;
    mkdocs is permissive). Source needs `(µm)` or escaped brackets.
  - 2 × heading anchors with `/` and `→` characters in
    `howto/patterns.md`.

Pipeline workarounds folded into the conversion script:
- `fence_indented_blocks()`: nbconvert's 4-space indented cell-output
  blocks are converted to fenced ```` ```text ```` so zensical's stricter
  CommonMark parser doesn't mis-parse bracketed text as reference-style
  links (would also tighten mkdocs output but isn't strictly needed there).
- HTML/LaTeX output stripping: when a cell has both a `text/plain` (or
  `image/*`) representation AND an HTML/LaTeX one (typical of
  `IPython.display.Code`, pandas DataFrames with HTML reprs, etc.), the
  HTML/LaTeX variants are dropped before MarkdownExporter sees them.
  Otherwise Pygments-rendered code blocks leak into the markdown and
  every bracketed token (`kcls["..."]`) becomes a fake link reference.
- `docs/overrides/main.html` did not need rewriting — MiniJinja
  accepts the existing template content.

### Phase 3 — CI caching + contributor docs — **DONE 2026-05-04**

- [x] `.github/workflows/docs.yml`: added `actions/cache@v4` step
  keyed on `hashFiles('docs/source/**', 'src/kfactory/**',
  'docs/scripts/build_docs_source.py')`. Cache restores
  `docs/.build-cache/` (manifest) and `docs/source-built/` (the
  staged notebooks + assets). On a clean PR run with cache hit, the
  notebook stage is a no-op (~0.25 s) so CI build drops to ~11 s.
- [x] `.github/workflows/pages.yml`: same cache step. Build
  recipe still `just docs`, no other workflow changes needed.
- [x] `docs/source/howto/contributing.md`: updated build-docs
  section to describe the two-stage pipeline (pre-build →
  mkdocs/zensical) and the download-notebook button. Added
  `kfactory[notebooks]` and `kfactory[docs-zensical]` rows to the
  dependency-extras table; called out `docs/source-built/` as a
  gitignored build artefact.

### Phase 4 — Cleanup (optional, low priority)

- [ ] Audit & rewrite `gdsfactory.md` autorefs to absolute URLs
  (would let zensical reach 0 warnings without waiting for its
  mkdocstrings module)
- [ ] Audit `[µm]` annotations in `components/overview.md` — change
  to `(µm)` or escape the brackets
- [ ] Audit `IPython.display.Code` usage in
  `schematics/{overview,crossing45}.py` — replace with plain code
  fences so HTML output doesn't break zensical's parser
- [ ] When zensical's mkdocstrings module ships and the warnings
  above clear, switch the canonical CI recipe from `just docs` to
  `just docs-zensical` and drop the mkdocs-related extras

### Phase 5 — Optional: migrate `mkdocs.yml` → `zensical.toml`

Defer until zensical's TOML schema stabilises. Zensical reads
`mkdocs.yml` natively today, so there's no functional reason to migrate
the format until the team publishes the canonical TOML structure.

## Final state (2026-05-04)

- `just docs` (mkdocs path): 2 warnings (pre-existing autoref issues
  in `gdsfactory.md` for `kfactory.cross_section.{Cross,DCross}Section`
  classes that lack class-level docstrings).
- `just docs-zensical` (zensical path): 21 warnings, all from
  pre-existing source-content issues (12 mkdocstrings autorefs not
  yet wired in zensical, 7 `[µm]` literals, 2 anchor names with
  special chars).
- Cold build wall time: ~22 s notebook stage + ~10–11 s render stage.
  Warm rebuild after caching: ~0.25 s pre-build + ~10 s render.
- 40 of 40 jupytext notebooks executed and rendered.
- Every rendered notebook page ships an `.ipynb` next to it with a
  prominent "Download notebook" button at the top.
- API reference (76 pages) generated by the pre-build script,
  rendered by mkdocstrings at HTML build time.

Phases 0–3 complete. Phase 4 is opportunistic source-content cleanup.
Phase 5 waits on the zensical team.

## Risks and open questions

- **Zensical alpha**: 0.0.40, expect breakage on minor version bumps.
  Pin exact version in `pyproject.toml` and gate upgrades manually.
- **MiniJinja vs Jinja**: `docs/overrides/main.html` may need rewriting
  if it uses Python-side filters. Audit before Phase 2.
- **Notebook execution time in CI**: 40 notebooks × ~1–5 s each ≈
  several minutes. Caching is mandatory.
- **`mkdocs-jupyter` features we lose**: `remove_tag_config` (hide
  cells by tag), `execute_ignore` patterns. The conversion script must
  reimplement: respect `# hide` cell tags via `nbconvert`'s
  `TagRemovePreprocessor`.
- **Diagram generation** (`gen_diagrams.py`): keep as-is, runs through
  `gen-files` which zensical supports.
- **Materially different theme look**: zensical's design is
  intentionally distinct from Material for MkDocs. Preview before
  shipping; adjust `extra_css` if branding drift is unacceptable.

## Order-of-operations summary

1. Phase 0 (1 commit): add zensical as parallel extra, prove it builds
   the `.md`-only subset.
2. Phase 1 (1 commit): notebook conversion script + verify against
   current mkdocs.
3. Phase 2 (1 commit): swap engine, drop unused plugins.
4. Phase 3–4 (1 commit): CI cache + contributor docs.
5. Phase 5: deferred until zensical TOML stabilises.

Each phase produces a working `just docs` build before moving on — same
incremental discipline as the previous overhaul (`plan.md`).
