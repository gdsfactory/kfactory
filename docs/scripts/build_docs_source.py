"""Pre-build docs source: jupytext .py → executed .md + downloadable .ipynb.

Replaces runtime mkdocs plugins (mkdocs-jupyter, mkdocs-gen-files) with
deterministic file generation into a staging directory. The static-site
generator (mkdocs or zensical) then sees only plain .md + assets.

Pipeline per source tree:
    docs/source/**/*.md   → copy verbatim to docs/source-built/
    docs/source/**/*.py   → jupytext.read → nbconvert.execute →
                            MarkdownExporter (+ TagRemovePreprocessor)
                            → docs/source-built/<path>.md  +
                              docs/source-built/<path>.ipynb (download)
                              + extracted output images
    docs/source/_static   → copy verbatim
    src/kfactory/**/*.py  → docs/source-built/reference/**/*.md
                            (mkdocstrings ::: directive stubs)
    schematic diagrams    → docs/source-built/_static/*.svg
                            (when --diagrams is passed; needs erdantic)

Cache: docs/.build-cache/manifest.json keyed by content hash; unchanged
inputs skip re-execution.

Usage:
    python docs/scripts/build_docs_source.py
        [--source docs/source] [--out docs/source-built]
        [--cache docs/.build-cache] [--workers N] [--no-execute]
        [--diagrams] [--clean]
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Any

import jupytext
import nbformat
from nbconvert import MarkdownExporter
from nbconvert.preprocessors import ExecutePreprocessor
from traitlets.config import Config

REPO_ROOT = Path(__file__).resolve().parents[2]


# Path to the layer-styles YAML and the generated .lyp.  The YAML follows
# kfactory.technology.layer_map.LypModel; we convert it once at build time
# and have every executed notebook load it via `as_png_data`'s
# `layer_properties` parameter.
DOC_STYLES_YAML = REPO_ROOT / "docs" / "source" / "_static" / "doc_styles.yaml"
DOC_STYLES_LYP = REPO_ROOT / "docs" / "source-built" / "_static" / "doc_styles.lyp"


def build_doc_styles_lyp() -> Path | None:
    """Convert docs/source/_static/doc_styles.yaml → .lyp.

    Returns the .lyp path on success, ``None`` if the YAML file is missing.
    """
    if not DOC_STYLES_YAML.exists():
        return None
    DOC_STYLES_LYP.parent.mkdir(parents=True, exist_ok=True)
    from kfactory.technology.layer_map import yaml_to_lyp

    yaml_to_lyp(DOC_STYLES_YAML, DOC_STYLES_LYP)
    return DOC_STYLES_LYP


# Setup cell injected at the top of every notebook.  Monkey-patches
# `kfactory.utilities.as_png_data` (and the re-export in
# `kfactory.widgets.interactive`) so it loads our generated .lyp by default.
# The .lyp matches each shape by (layer, datatype) — see the layer
# convention documented in `_static/doc_styles.yaml`.
_DOC_STYLE_SETUP = """\
def _kf_apply_doc_styles() -> None:
    from pathlib import Path
    import kfactory.utilities
    import kfactory.widgets.interactive

    _lyp = Path({lyp_path!r})
    if not _lyp.is_file():
        return
    _original = kfactory.utilities.as_png_data

    def _styled_as_png_data(c, layer_properties=None, **kwargs):
        return _original(c, layer_properties=layer_properties or str(_lyp), **kwargs)

    kfactory.utilities.as_png_data = _styled_as_png_data
    kfactory.widgets.interactive.as_png_data = _styled_as_png_data


_kf_apply_doc_styles()
"""


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def cache_load(cache_dir: Path) -> dict[str, str]:
    f = cache_dir / "manifest.json"
    if not f.exists():
        return {}
    try:
        return json.loads(f.read_text())
    except json.JSONDecodeError:
        return {}


def cache_save(cache_dir: Path, manifest: dict[str, str]) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True)
    )


def cache_key(input_path: Path, *output_paths: Path) -> str:
    return f"{input_path}::{':'.join(str(p) for p in output_paths)}"


def compute_source_fingerprint(repo_root: Path) -> dict[str, str | None]:
    """Snapshot identifying the current `src/kfactory/` source-tree state.

    Returns ``{"head_oid": ..., "src_hash": ...}``.  ``head_oid`` is the
    SHA of the current git HEAD or ``None`` if pygit2 can't open the
    working tree as a git repo (source tarball, CI checkout without
    ``.git``, unborn HEAD, …).  ``src_hash`` is an order-independent
    SHA256 over every ``.py`` file under ``src/kfactory/`` so working-tree
    edits invalidate the notebook cache even on a clean HEAD.
    """
    head_oid: str | None = None
    try:
        import pygit2

        repo = pygit2.Repository(str(repo_root))
        head_oid = str(repo.head.target)
    except Exception:
        head_oid = None

    src_root = repo_root / "src" / "kfactory"
    src_h = hashlib.sha256()
    if src_root.exists():
        for path in sorted(src_root.rglob("*.py")):
            src_h.update(str(path.relative_to(repo_root)).encode())
            src_h.update(b"\0")
            src_h.update(path.read_bytes())
            src_h.update(b"\0")
    return {"head_oid": head_oid, "src_hash": src_h.hexdigest()}


def fingerprint_load(cache_dir: Path) -> dict[str, str | None]:
    f = cache_dir / "fingerprint.json"
    if not f.exists():
        return {}
    try:
        return json.loads(f.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def fingerprint_save(cache_dir: Path, fp: dict[str, str | None]) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "fingerprint.json").write_text(json.dumps(fp, indent=2))


_PY_LINK_RE = re.compile(r"(\]\((?!https?://)[^)]+?)\.py(#[^)]*)?\)")


def rewrite_py_links(text: str) -> str:
    """Rewrite Markdown links from foo.py → foo.md (skips http(s) URLs)."""
    return _PY_LINK_RE.sub(lambda m: f"{m.group(1)}.md{m.group(2) or ''})", text)


def fence_indented_blocks(text: str) -> str:
    """Convert nbconvert's indented (4-space) code blocks to fenced ```text
    blocks. Zensical's CommonMark parser incorrectly parses reference-style
    links inside indented blocks, but respects fenced blocks. Lines inside
    existing fenced blocks (```) are passed through untouched.
    """
    out: list[str] = []
    lines = text.splitlines(keepends=False)
    i = 0
    in_fence = False
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
            out.append(line)
            i += 1
            continue
        if (
            not in_fence
            and line.startswith("    ")
            and (i == 0 or lines[i - 1].strip() == "")
        ):
            # Collect a contiguous indented block (4-space-prefixed lines,
            # blank lines allowed inside as long as the next non-blank also
            # starts with 4 spaces).
            block: list[str] = []
            while i < len(lines):
                cur = lines[i]
                if cur.startswith("    "):
                    block.append(cur[4:])
                    i += 1
                elif cur.strip() == "":
                    # Lookahead: continue only if the next non-blank line
                    # is also indented (still part of the block).
                    j = i + 1
                    while j < len(lines) and lines[j].strip() == "":
                        j += 1
                    if j < len(lines) and lines[j].startswith("    "):
                        block.append("")
                        i += 1
                    else:
                        break
                else:
                    break
            out.append("```text")
            out.extend(block)
            out.append("```")
            continue
        out.append(line)
        i += 1
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


def copy_md(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    text = src.read_text()
    new = rewrite_py_links(text)
    if new == text:
        shutil.copy2(src, dst)
    else:
        dst.write_text(new)


def copy_static(src_dir: Path, dst_dir: Path) -> None:
    if not src_dir.exists():
        return
    if dst_dir.exists():
        shutil.rmtree(dst_dir)
    shutil.copytree(src_dir, dst_dir)


def is_jupytext_notebook(path: Path) -> bool:
    """Detect jupytext percent-format .py by header signature."""
    if path.suffix != ".py":
        return False
    try:
        head = path.read_text(errors="replace").splitlines()[:20]
    except OSError:
        return False
    return any(line.strip().startswith("# %%") for line in head) or any(
        "jupytext:" in line for line in head
    )


def convert_notebook(
    src: Path,
    src_root: Path,
    out_root: Path,
    *,
    execute: bool = True,
    timeout: int = 600,
) -> tuple[Path, Path]:
    """Convert a jupytext .py to executed .ipynb + .md.

    Returns (md_path, ipynb_path).
    """
    rel = src.relative_to(src_root)
    md_out = out_root / rel.with_suffix(".md")
    # Place .ipynb inside the page's asset directory so the relative
    # download link resolves under mkdocs use_directory_urls (page at
    # foo/index.html ↔ asset at foo/foo.ipynb).
    assets_dir = md_out.with_suffix("")
    assets_dir.mkdir(parents=True, exist_ok=True)
    ipynb_out = assets_dir / f"{rel.stem}.ipynb"
    md_out.parent.mkdir(parents=True, exist_ok=True)

    nb = jupytext.read(src, fmt="py:percent")
    if "kernelspec" not in nb.metadata:
        nb.metadata["kernelspec"] = {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        }

    # Inject a hidden setup cell at the top that points
    # `kfactory.utilities.as_png_data` at our generated .lyp so every
    # rendered notebook PNG picks up the documentation layer styles.
    setup_cell = nbformat.v4.new_code_cell(
        _DOC_STYLE_SETUP.format(lyp_path=str(DOC_STYLES_LYP))
    )
    setup_cell.metadata["tags"] = ["hide-input", "hide-output", "hide"]
    nb.cells.insert(0, setup_cell)

    if execute:
        ep = ExecutePreprocessor(timeout=timeout, kernel_name="python3")
        ep.preprocess(nb, {"metadata": {"path": str(src.parent)}})

    nbformat.write(nb, ipynb_out)

    # Drop text/html and text/latex outputs in favour of text/plain or
    # images. nbconvert otherwise inlines Pygments-rendered HTML/LaTeX for
    # things like IPython.display.Code(), and the bracketed Python code
    # inside those blocks gets mis-parsed by CommonMark as reference-style
    # links. Plain-text fallback round-trips cleanly through fenced code.
    for cell in nb.cells:
        if cell.cell_type != "code":
            continue
        for out in cell.get("outputs", []):
            data = out.get("data") or {}
            has_fallback = "text/plain" in data or any(
                k.startswith("image/") for k in data
            )
            if has_fallback:
                for k in ("text/html", "text/latex"):
                    data.pop(k, None)

    cfg = Config()
    cfg.TagRemovePreprocessor.remove_input_tags = ("hide", "hide-input")
    cfg.TagRemovePreprocessor.remove_all_outputs_tags = ("hide", "hide-output")
    cfg.TagRemovePreprocessor.enabled = True
    cfg.MarkdownExporter.preprocessors = [
        "nbconvert.preprocessors.TagRemovePreprocessor"
    ]

    exporter = MarkdownExporter(config=cfg)
    body, resources = exporter.from_notebook_node(nb)

    # Write extracted output images into the assets directory
    outputs: dict[str, bytes] = resources.get("outputs", {}) or {}
    for name, data in outputs.items():
        (assets_dir / name).write_bytes(data)
    # nbconvert references images by bare basename; rewrite to the
    # assets_dir we just wrote (same name as the page, no suffix).
    for name in outputs:
        body = body.replace(f"]({name})", f"]({assets_dir.name}/{name})")

    # Rewrite cross-page Markdown links from .py → .md so the converted
    # notebooks resolve siblings correctly under mkdocs/zensical. Runs
    # before the download-button injection so the .ipynb link is safe.
    body = rewrite_py_links(body)
    # Convert nbconvert's indented cell-output blocks to fenced blocks
    # so zensical's stricter CommonMark parser doesn't mis-parse text
    # like `['name1', 'name2']` as reference-style links.
    body = fence_indented_blocks(body)

    # Link points into the assets dir: foo.md → foo/foo.ipynb.
    # Under use_directory_urls=true the rendered page sits at
    # foo/index.html so the relative path becomes simply foo.ipynb.
    download_btn = (
        f"[:material-download: Download notebook (.ipynb)]"
        f"({assets_dir.name}/{ipynb_out.name}){{ .md-button }}\n\n"
    )
    md_out.write_text(download_btn + body)
    return md_out, ipynb_out


def gen_api_reference(out_root: Path, src_pkg: Path) -> list[Path]:
    """Mirror src/kfactory/**/*.py to out_root/reference/**/*.md with
    mkdocstrings ::: directive stubs. Replaces gen_ref_pages.py.

    URL layout (drops the redundant `kfactory/` prefix):
        kfactory/__init__.py          → reference/index.md         (`::: kfactory`)
        kfactory/cells/__init__.py    → reference/cells/index.md   (`::: kfactory.cells`)
        kfactory/cells/bezier.py      → reference/cells/bezier.md  (`::: kfactory.cells.bezier`)
    so that `/reference/` itself is the top-level package API page,
    not a "click here to see the API" detour.
    """
    # Wipe any previously-generated reference tree so a module removed
    # from src/kfactory/ doesn't leave an orphan `::: kfactory.foo` page
    # behind. CI restores docs/source-built/ via actions/cache restore-keys
    # when the hash changes, and a stale directive for a now-removed
    # module crashes mkdocstrings during the zensical build.
    ref_root = out_root / "reference"
    if ref_root.exists():
        shutil.rmtree(ref_root)

    written: list[Path] = []
    # Tree of (depth, title, doc_rel) preserving traversal order.
    # Used to splice the API nav into zensical.yml since zensical 0.0.40
    # doesn't render `literate-nav` SUMMARY.md into the side panel.
    api_tree: list[tuple[int, str, str]] = []

    for py in sorted(src_pkg.rglob("*.py")):
        rel = py.relative_to(src_pkg.parent)  # e.g. kfactory/cells/bezier.py
        parts = list(rel.with_suffix("").parts)
        if parts[-1] == "__main__":
            continue
        is_package = parts[-1] == "__init__"
        if is_package:
            parts = parts[:-1]
            sub_parts = parts[1:]  # drop leading "kfactory"
            doc_rel = (
                Path("index.md") if not sub_parts else Path(*sub_parts) / "index.md"
            )
        else:
            sub_parts = parts[1:]  # drop leading "kfactory"
            doc_rel = Path(*sub_parts).with_suffix(".md")
        target = out_root / "reference" / doc_rel
        target.parent.mkdir(parents=True, exist_ok=True)
        ident = ".".join(parts)
        # Package pages: render the package docstring only (members: false).
        # Re-exports would otherwise pull in the entire library on the
        # top-level page. Leaf modules render full mkdocstrings content.
        # Submodule navigation goes through the side nav, which the build
        # script splices into zensical.yml from `api_tree` below.
        if is_package:
            target.write_text(f"::: {ident}\n    options:\n      members: false\n")
        else:
            target.write_text(f"::: {ident}\n")
        written.append(target)
        depth = max(len(parts) - 1, 0)
        title = parts[-1] if parts else "kfactory"
        api_tree.append((depth, title, doc_rel.as_posix()))

    # Build the YAML fragment for splicing into zensical.yml's nav.
    # Format: nested mapping so the API tab in the side nav has a tree.
    api_nav_yaml = _api_tree_to_yaml(api_tree, indent=10)
    (out_root / "_api_nav.yml").write_text(api_nav_yaml)
    return written


def _api_tree_to_yaml(tree: list[tuple[int, str, str]], indent: int = 0) -> str:
    """Render the flat DFS-order (depth, title, doc_rel) list as a nested
    YAML nav fragment. Entries whose next sibling has greater depth are
    treated as subpackage headers; their `index.md` is rendered as an
    "Overview" child below the header.

    Output (indent=10):
              - Overview: reference/index.md
              - cells:
                  - Overview: reference/cells/index.md
                  - bezier: reference/cells/bezier.md
                  - virtual:
                      - Overview: reference/cells/virtual/index.md
                      - circular: reference/cells/virtual/circular.md
              - cli: reference/cli.md
              ...
    """
    n = len(tree)
    is_pkg = [i + 1 < n and tree[i + 1][0] > tree[i][0] for i in range(n)]
    pad = " " * indent
    lines: list[str] = []
    for i, (depth, title, doc_rel) in enumerate(tree):
        # Tree depth 0 = root package (kfactory); its direct children
        # become siblings of "Overview" so the side-nav doesn't have
        # a redundant "kfactory:" wrapper. Effective indent column:
        # depth 0 and 1 → 0, depth 2 → 4, depth 3 → 8, …
        col = pad + ("    " * max(0, depth - 1))
        link = f"reference/{doc_rel}"
        if depth == 0 and is_pkg[i]:
            lines.append(f"{col}- Overview: {link}")
        elif is_pkg[i]:
            lines.append(f"{col}- {title}:")
            lines.append(f"{col}    - Overview: {link}")
        else:
            lines.append(f"{col}- {title}: {link}")
    return "\n".join(lines) + "\n"


def splice_zensical_config(
    src_yml: Path, out_yml: Path, api_nav_fragment: Path
) -> None:
    """Replace `- API: reference/   # SPLICE_API` in src_yml with
       - API:
         <fragment children>
    written to out_yml. Plain text replacement (preserves the rest of
    the YAML's comments + formatting); zensical's YAML loader still
    validates it.
    """
    text = src_yml.read_text()
    marker_re = re.compile(
        r"^([ \t]*)- API:[ \t]*reference/[ \t]*#[ \t]*SPLICE_API[ \t]*$",
        re.MULTILINE,
    )
    match = marker_re.search(text)
    if not match:
        raise RuntimeError(
            f"Could not find `# SPLICE_API` marker in {src_yml}; the "
            "API nav block won't be auto-generated. Add the marker back "
            "or update the regex in build_docs_source.py."
        )
    indent = match.group(1)
    fragment = api_nav_fragment.read_text().rstrip("\n")
    spliced = f"{indent}- API:\n{fragment}"
    out_yml.write_text(marker_re.sub(spliced, text, count=1))


def gen_diagrams(out_root: Path) -> list[Path]:
    """Generate erdantic schematic diagrams. Skipped if erdantic is
    missing (local dev without graphviz). Replaces gen_diagrams.py.
    """
    try:
        import erdantic as erd  # type: ignore[import-not-found]
    except ImportError:
        print("[diagrams] erdantic not installed — skipping", flush=True)
        return []

    import kfactory as kf

    static_dir = out_root / "_static"
    static_dir.mkdir(parents=True, exist_ok=True)

    class DSchematic(kf.schematic.TSchematic[float]):  # type: ignore[name-defined]
        __doc__ = kf.Schematic.__doc__

    class Schematic(kf.schematic.TSchematic[int]):  # type: ignore[name-defined]
        __doc__ = kf.Schematic.__doc__

    diagram_dbu = erd.create(Schematic, terminal_models=[kf.KCLayout])
    diagram_dbu.models["kfactory.layout.KCLayout"].fields = {}
    out_dbu = static_dir / "schematic.svg"
    diagram_dbu.draw(out_dbu)

    diagram_um = erd.create(DSchematic, terminal_models=[kf.KCLayout])
    diagram_um.models["kfactory.layout.KCLayout"].fields = {}
    out_um = static_dir / "dschematic.svg"
    diagram_um.draw(out_um)
    return [out_dbu, out_um]


def process_one(args: tuple[Path, Path, Path, bool, int]) -> dict[str, Any]:
    src, src_root, out_root, execute, timeout = args
    t0 = time.perf_counter()
    md, ipynb = convert_notebook(
        src, src_root, out_root, execute=execute, timeout=timeout
    )
    return {
        "src": str(src),
        "md": str(md),
        "ipynb": str(ipynb),
        "elapsed": time.perf_counter() - t0,
        "hash": file_hash(src),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=str(REPO_ROOT / "docs/source"))
    parser.add_argument("--out", default=str(REPO_ROOT / "docs/source-built"))
    parser.add_argument("--cache", default=str(REPO_ROOT / "docs/.build-cache"))
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--no-execute", action="store_true")
    parser.add_argument("--diagrams", action="store_true")
    parser.add_argument("--clean", action="store_true")
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        help="Only convert notebooks whose path contains this substring",
    )
    args = parser.parse_args(argv)

    src_root = Path(args.source).resolve()
    out_root = Path(args.out).resolve()
    cache_dir = Path(args.cache).resolve()

    if args.clean and out_root.exists():
        shutil.rmtree(out_root)
    out_root.mkdir(parents=True, exist_ok=True)

    manifest = cache_load(cache_dir)
    new_manifest = dict(manifest)

    # Invalidate the notebook cache if the source tree has moved since it
    # was built — either a different git HEAD or any edit to
    # `src/kfactory/**/*.py` in the working tree.  Without this, source
    # edits don't trigger a notebook re-execution.
    current_fp = compute_source_fingerprint(REPO_ROOT)
    cached_fp = fingerprint_load(cache_dir)
    if (
        cached_fp.get("head_oid") != current_fp["head_oid"]
        or cached_fp.get("src_hash") != current_fp["src_hash"]
    ):
        if cached_fp:
            print(
                "[cache] git HEAD or src/kfactory changed → invalidating notebook cache"
            )
        manifest = {}
        new_manifest = {}

    # Stage 1: copy .md files
    md_count = 0
    for md in src_root.rglob("*.md"):
        rel = md.relative_to(src_root)
        copy_md(md, out_root / rel)
        md_count += 1

    # Stage 1b: copy static asset directories (anything under _static)
    for static_dir in src_root.rglob("_static"):
        if static_dir.is_dir():
            rel = static_dir.relative_to(src_root)
            copy_static(static_dir, out_root / rel)

    # Stage 1c: generate the layer-styles .lyp from YAML.  Must run AFTER
    # Stage 1b because copy_static wipes the destination _static/ tree.
    lyp = build_doc_styles_lyp()
    if lyp is not None:
        print(f"[stage1c] doc layer styles → {lyp.relative_to(REPO_ROOT)}")

    # Stage 2: jupytext .py → .md + .ipynb
    notebooks = [p for p in src_root.rglob("*.py") if is_jupytext_notebook(p)]
    if args.only:
        notebooks = [p for p in notebooks if any(s in str(p) for s in args.only)]

    work: list[tuple[Path, Path, Path, bool, int]] = []
    skipped = 0
    for nb in notebooks:
        h = file_hash(nb)
        key = cache_key(nb, out_root)
        if manifest.get(key) == h:
            rel = nb.relative_to(src_root)
            md_path = out_root / rel.with_suffix(".md")
            ipynb_path = md_path.with_suffix("") / f"{rel.stem}.ipynb"
            if md_path.exists() and ipynb_path.exists():
                skipped += 1
                # Carry forward the cached entry so a later --clean
                # of source-built doesn't strand the manifest.
                new_manifest[key] = h
                continue
        work.append((nb, src_root, out_root, not args.no_execute, args.timeout))

    print(
        f"[stage1] copied {md_count} .md files",
        f"[stage2] {len(work)} notebooks to convert ({skipped} cached)",
        sep="\n",
        flush=True,
    )

    failures: list[tuple[Path, BaseException]] = []
    if work:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
            futures = {ex.submit(process_one, w): w[0] for w in work}
            for fut in concurrent.futures.as_completed(futures):
                src = futures[fut]
                try:
                    res = fut.result()
                    new_manifest[cache_key(Path(res["src"]), out_root)] = res["hash"]
                    print(
                        f"  ✓ {Path(res['src']).relative_to(src_root)} "
                        f"({res['elapsed']:.1f}s)",
                        flush=True,
                    )
                except BaseException as e:
                    failures.append((src, e))
                    print(f"  ✗ {src.relative_to(src_root)}: {e}", flush=True)

    # Stage 3: API reference
    print("[stage3] generating API reference …", flush=True)
    ref_files = gen_api_reference(out_root, REPO_ROOT / "src" / "kfactory")
    print(f"  wrote {len(ref_files)} reference pages", flush=True)

    # Stage 3.5: splice API nav into zensical.yml → docs/zensical-built.yml
    src_cfg = REPO_ROOT / "docs/zensical.yml"
    spliced_cfg = REPO_ROOT / "docs/zensical-built.yml"
    fragment = out_root / "_api_nav.yml"
    splice_zensical_config(src_cfg, spliced_cfg, fragment)
    print(f"[stage3.5] wrote {spliced_cfg.relative_to(REPO_ROOT)}", flush=True)

    # Stage 4: logo (κ generated from a real kfactory KCell → GDS + SVG)
    print("[stage4] generating κ logo …", flush=True)
    from gen_logo import generate as generate_logo

    logo_gds, logo_svg = generate_logo(out_root / "_static")
    print(f"  wrote {logo_gds.name} + {logo_svg.name}", flush=True)

    # Stage 5: diagrams (optional)
    if args.diagrams:
        print("[stage5] generating diagrams …", flush=True)
        diag_files = gen_diagrams(out_root)
        print(f"  wrote {len(diag_files)} diagram(s)", flush=True)

    cache_save(cache_dir, new_manifest)
    fingerprint_save(cache_dir, current_fp)

    if failures:
        print(f"\n{len(failures)} notebook(s) failed:", file=sys.stderr)
        for src, e in failures:
            print(f"  {src}: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
