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
from nbconvert.preprocessors import ExecutePreprocessor, TagRemovePreprocessor
from traitlets.config import Config

REPO_ROOT = Path(__file__).resolve().parents[2]


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


_PY_LINK_RE = re.compile(r"(\]\((?!https?://)[^)]+?)\.py(#[^)]*)?\)")


def rewrite_py_links(text: str) -> str:
    """Rewrite Markdown links from foo.py → foo.md (skips http(s) URLs)."""
    return _PY_LINK_RE.sub(
        lambda m: f"{m.group(1)}.md{m.group(2) or ''})", text
    )


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
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            out.append(line)
            i += 1
            continue
        if not in_fence and line.startswith("    ") and (
            i == 0 or lines[i - 1].strip() == ""
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
    """
    written: list[Path] = []
    nav_lines: list[str] = []
    for py in sorted(src_pkg.rglob("*.py")):
        rel = py.relative_to(src_pkg.parent)  # relative to src/
        parts = list(rel.with_suffix("").parts)
        if parts[-1] == "__main__":
            continue
        if parts[-1] == "__init__":
            parts = parts[:-1]
            doc_rel = rel.with_name("index.md")
        else:
            doc_rel = rel.with_suffix(".md")
        target = out_root / "reference" / doc_rel
        target.parent.mkdir(parents=True, exist_ok=True)
        ident = ".".join(parts)
        target.write_text(f"::: {ident}\n")
        written.append(target)
        # SUMMARY.md indentation = nesting depth - 1 (kfactory itself is depth 1)
        depth = max(len(parts) - 1, 0)
        title = parts[-1] if parts else "kfactory"
        link = doc_rel.as_posix()
        nav_lines.append(f"{'    ' * depth}* [{title}]({link})")
    summary = out_root / "reference" / "SUMMARY.md"
    summary.write_text("\n".join(nav_lines) + "\n")
    written.append(summary)

    # Section landing page so the "API" tab itself resolves (without it
    # the URL `/reference/` 404s — only the per-module pages exist).
    index = out_root / "reference" / "index.md"
    index.write_text(
        "# API Reference\n\n"
        "Auto-generated from kfactory's source tree. Browse the modules in "
        "the side panel, or jump straight to the [top-level package]"
        "(kfactory/index.md).\n"
    )
    written.append(index)
    return written


def gen_diagrams(out_root: Path) -> list[Path]:
    """Generate erdantic schematic diagrams. Skipped if erdantic is
    missing (local dev without graphviz). Replaces gen_diagrams.py.
    """
    try:
        import erdantic as erd  # type: ignore[import-not-found]
    except ImportError:
        print("[diagrams] erdantic not installed — skipping", flush=True)
        return []

    import kfactory as kf  # noqa: F401 — needed for class refs below

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
                except BaseException as e:  # noqa: BLE001
                    failures.append((src, e))
                    print(f"  ✗ {src.relative_to(src_root)}: {e}", flush=True)

    # Stage 3: API reference
    print("[stage3] generating API reference …", flush=True)
    ref_files = gen_api_reference(out_root, REPO_ROOT / "src" / "kfactory")
    print(f"  wrote {len(ref_files)} reference pages", flush=True)

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

    if failures:
        print(f"\n{len(failures)} notebook(s) failed:", file=sys.stderr)
        for src, e in failures:
            print(f"  {src}: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
