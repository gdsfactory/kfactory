# Existing Content Migration Map

Where current docs content goes in the new structure.

## Markdown files

| Current file | Action | New location |
|---|---|---|
| `source/index.md` | Keep + expand | `source/index.md` (add quick-nav cards) |
| `source/gdsfactory.md` | Keep + expand | `source/gdsfactory.md` (add routing/cross-section comparison) |
| `source/dosdonts.md` | **Delete** (13 lines, replaced) | Content superseded by `howto/best_practices.py` |
| `source/pre.md` | **Split** | `getting_started/prerequisites.md` + `getting_started/installation.md` |
| `source/intro.md` | **Convert to notebook** | `getting_started/quickstart.py` |
| `source/pcells.md` | **Convert to notebook** | `components/pcells.py` |
| `source/migration.md` | Keep + expand | `source/migration.md` (add summary table) |
| `source/config.md` | Keep + expand | `source/config.md` (add env var table at top) |
| `source/changelog.md` | Keep | `source/changelog.md` |

## Notebooks (.py jupytext files)

| Current file | Action | New location |
|---|---|---|
| `notebooks/00_geometry.py` (17 KB) | **Absorb** into concepts | `concepts/geometry.py` — take all content, expand with Region/boolean ops |
| `notebooks/01_references.py` (9.6 KB) | **Split** into two pages | `concepts/ports.py` (port sections) + `concepts/instances.py` (instance sections) |
| `notebooks/02_DRC.py` (6 KB) | **Absorb** into utilities | `utilities/drc_fix.py` |
| `notebooks/03_Enclosures.py` (4.7 KB) | **Absorb** into enclosures | `enclosures/layer_enclosure.py` |
| `notebooks/04_KCL.py` (2.8 KB) | **Absorb** into concepts | `concepts/kclayout.py` |
| `notebooks/05_Schematics.py` (25 KB) | **Absorb** into schematics | `schematics/overview.py` (restructured with better narrative) |

## Root helper .py files

| Current file | Action |
|---|---|
| `source/complex_cell.py` | Move to `source/_examples/` or keep (excluded by `ignore` pattern) |
| `source/layers.py` | Move to `source/_examples/` or keep |
| `source/star.py` | Move to `source/_examples/` or keep |
| `source/straight.py` | Move to `source/_examples/` or keep |

These are referenced via `--8<--` snippets from some .md files. Check references before moving.

## Static assets (keep as-is)

| File | Used by |
|---|---|
| `_static/complex.png` | intro.md |
| `_static/waveguide.png` | intro.md |
| `_static/schematic.svg` | 05_Schematics.py |
| `_static/dschematic.svg` | 05_Schematics.py |
| `_static/klive.webm` | pre.md -> getting_started/klive_setup.md |
