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

# %% [markdown]
# # Session Cache
#
# Computing cells with `@kf.cell` is fast for small components, but a full
# PDK with hundreds of parameterised cells can take seconds to rebuild from
# scratch on every import.  The **session cache** persists the factory
# cell-cache to disk so that subsequent runs skip cells whose factory source
# code has not changed.
#
# | Function | What it does |
# |---|---|
# | `kf.save_session(c=None, session_dir=None)` | Serialise all factory caches to `build/session/kcls/` (or a custom path) |
# | `kf.load_session(session_dir=None, warn_missing_dir=True)` | Restore factory caches from disk; cells whose factory source changed are silently skipped |
#
# **Only cells created by a `@kf.cell`-decorated factory** are included in
# the cache.  Ad-hoc cells (built without a decorator) are not saved.

# %% [markdown]
# ## Setup
#
# `save_session` hashes each factory's **source file on disk** so it can detect
# changes on the next load.  For this demo we write a small factory module to a
# temporary file and import it.  In a real project your PDK is already a proper
# Python package, so factory source files always exist on disk.

# %%
import importlib.util
import pathlib
import shutil
import tempfile

import kfactory as kf

tmpdir = pathlib.Path(tempfile.mkdtemp(prefix="kf_session_demo_"))

factory_src = '''\
import kfactory as kf

class LAYER(kf.LayerInfos):
    WG: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 0)

L = LAYER()
pdk = kf.KCLayout("SESSION_DEMO", infos=LAYER)


@pdk.cell
def wg_straight(width: float = 0.5, length: float = 10.0) -> kf.KCell:
    """Straight waveguide."""
    c = kf.KCell(kcl=pdk)
    wg_layer = pdk.find_layer(L.WG)
    w = pdk.to_dbu(width)
    length_dbu = pdk.to_dbu(length)
    c.shapes(wg_layer).insert(
        kf.kdb.Box(-length_dbu // 2, -w // 2, length_dbu // 2, w // 2)
    )
    c.add_port(port=kf.Port(name="o1",
                             trans=kf.kdb.Trans(2, False, -length_dbu // 2, 0),
                             width=w, layer=wg_layer, kcl=pdk))
    c.add_port(port=kf.Port(name="o2",
                             trans=kf.kdb.Trans(0, False, length_dbu // 2, 0),
                             width=w, layer=wg_layer, kcl=pdk))
    return c


@pdk.cell
def wg_taper(w1: float = 0.5, w2: float = 1.0, length: float = 20.0) -> kf.KCell:
    """Linear taper."""
    c = kf.KCell(kcl=pdk)
    wg_layer = pdk.find_layer(L.WG)
    w1_dbu = pdk.to_dbu(w1)
    w2_dbu = pdk.to_dbu(w2)
    l_dbu = pdk.to_dbu(length)
    pts = [
        kf.kdb.Point(-l_dbu // 2, -w1_dbu // 2),
        kf.kdb.Point(-l_dbu // 2, w1_dbu // 2),
        kf.kdb.Point(l_dbu // 2, w2_dbu // 2),
        kf.kdb.Point(l_dbu // 2, -w2_dbu // 2),
    ]
    c.shapes(wg_layer).insert(kf.kdb.Polygon(pts))
    c.add_port(port=kf.Port(name="o1",
                             trans=kf.kdb.Trans(2, False, -l_dbu // 2, 0),
                             width=w1_dbu, layer=wg_layer, kcl=pdk))
    c.add_port(port=kf.Port(name="o2",
                             trans=kf.kdb.Trans(0, False, l_dbu // 2, 0),
                             width=w2_dbu, layer=wg_layer, kcl=pdk))
    return c
'''

module_file = tmpdir / "demo_factories.py"
module_file.write_text(factory_src)

spec = importlib.util.spec_from_file_location("demo_factories", module_file)
assert spec is not None and spec.loader is not None
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)  # type: ignore[union-attr]

pdk = demo.pdk
wg_straight = demo.wg_straight
wg_taper = demo.wg_taper

# %% [markdown]
# ## Step 1 — Call `load_session` at startup (before computing anything)
#
# The canonical usage is to call `load_session` **at the top of your PDK
# module**, before any factory functions are defined or called.  On the very
# first run no session exists yet, so `load_session` logs a warning and
# returns immediately.  Pass `warn_missing_dir=False` to suppress that warning
# in production.

# %%
session_dir = tmpdir / "session"

# First run: no session exists yet.  warn_missing_dir=False suppresses the log.
kf.load_session(session_dir=session_dir, warn_missing_dir=False)
print("load_session on first run: no session yet, nothing loaded")

# %% [markdown]
# ## Step 2 — Build cells as usual

# %%
wg_500 = wg_straight(width=0.5, length=10.0)
wg_800 = wg_straight(width=0.8, length=20.0)
taper_a = wg_taper(w1=0.5, w2=1.0, length=20.0)
taper_b = wg_taper(w1=0.5, w2=2.0, length=40.0)

print("Cells in pdk:", [pdk[i].name for i in range(pdk.cells())])
print("wg_straight cache size:", len(pdk.factories["wg_straight"].cache))
print("wg_taper    cache size:", len(pdk.factories["wg_taper"].cache))

# %% [markdown]
# ## Step 3 — Save the session at the end of the build
#
# `kf.save_session()` serialises every populated factory cache across all
# registered `KCLayout` instances.  Default location: `build/session/kcls/`
# (auto-created and auto-added to `.gitignore`).

# %%
kf.save_session(session_dir=session_dir)

print("Saved files:")
for f in sorted(session_dir.rglob("*")):
    print(" ", f.relative_to(tmpdir))

# %% [markdown]
# kfactory writes two files per layout:
#
# * **`cells.gds.gz`** — compressed GDS containing geometry of all
#   factory-cached cells
# * **`factories.pkl`** — factory name → cached cell names + SHA-256 hash of
#   each factory's source file (used for invalidation)
#
# A top-level **`kcl_dependencies.json`** records which layouts depend on
# which, so `load_session` can restore them in the correct dependency order.

# %% [markdown]
# ## How invalidation works
#
# On each `load_session` call, kfactory re-hashes every registered factory's
# source `.py` file and compares it to the stored hash.  If the file has
# changed — or if a factory that depends on the changed factory is found —
# those cells are **skipped** (not loaded from disk) and will be recomputed
# fresh on the next call.  This means you never silently serve stale geometry.
#
# ```
# Factory source unchanged  →  cells restored from disk (fast path)
# Factory source changed     →  cells skipped → recomputed on next call
# Factory depends on changed →  also skipped (transitive invalidation)
# ```

# %% [markdown]
# ## Saving only a subset
#
# Pass `c=<cell>` to restrict saving to only the `KCLayout` instances needed
# by that specific cell.  Useful in monorepo setups where multiple independent
# PDKs share one Python process.

# %%
subset_dir = tmpdir / "session_subset"
kf.save_session(c=wg_500, session_dir=subset_dir)

print("Subset save — files:")
for f in sorted(subset_dir.rglob("*")):
    print(" ", f.relative_to(tmpdir))

# %% [markdown]
# ## Complete usage pattern
#
# ```python
# # my_pdk/__init__.py
# import kfactory as kf
#
# pdk = kf.KCLayout("my_pdk", infos=LAYER)
#
# # Restore previously-computed cells before defining factories.
# # Silently skips on the very first run when no session exists yet.
# kf.load_session(warn_missing_dir=False)
#
# @pdk.cell
# def wg_straight(...) -> kf.KCell:
#     ...
#
# @pdk.cell
# def euler_bend(...) -> kf.KCell:
#     ...
# ```
#
# ```python
# # build_chip.py
# import my_pdk           # load_session() runs here at import time
# import kfactory as kf
#
# chip = my_pdk.assemble_chip()
# chip.write_gds("output/chip.gds")
#
# # Persist the cache so the next run is faster.
# kf.save_session()
# ```

# %% [markdown]
# ## Summary
#
# | Scenario | Call |
# |---|---|
# | Large PDK, speed up re-imports | `load_session(warn_missing_dir=False)` at module top; `save_session()` at build end |
# | Save only one PDK in a multi-PDK process | `save_session(c=my_top_cell)` |
# | Custom CI cache location | `save_session(session_dir=Path(".cache/kf"))` and matching `load_session(...)` |
# | Suppress "no session dir" warning | `load_session(warn_missing_dir=False)` |
#
# > **Tip:** The default session directory (`build/session/kcls/`) is
# > auto-added to `.gitignore`.  Never commit session files — they are
# > machine-specific build artefacts.

# %%
# Clean up temp directories used in this notebook.
shutil.rmtree(tmpdir, ignore_errors=True)

# %% [markdown]
# ## See Also
#
# | Topic | Where |
# |-------|-------|
# | Layout regression testing | [Utilities: Difftest](difftest.py) |
# | Creating a full PDK | [PDK: Creating a PDK](../pdk/creating_pdk.py) |
# | KCLayout (owns the cell DB) | [Core Concepts: KCLayout](../concepts/kclayout.py) |
