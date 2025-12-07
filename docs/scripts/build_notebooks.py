"""Build notebooks from Python files in docs/source/notebooks."""

import subprocess
from pathlib import Path


def build_notebooks():
    """Convert .py files to notebooks and then to markdown."""
    source_dir = Path(__file__).parent.parent / "source"

    # Find all .py files in the source directory recursively
    py_files = sorted(source_dir.glob("**/*.py"))

    if not py_files:
        print(f"No .py files found in {source_dir}")
        return

    print(f"Found {len(py_files)} Python files to convert")

    for py_file in py_files:
        print(f"\nProcessing {py_file.name}...")

        # Convert .py to .ipynb using jupytext
        print(f"  Converting to notebook...")
        result = subprocess.run(
            ["uv", "run", "jupytext", "--to", "notebook", str(py_file)],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print(f"  Error converting {py_file.name}: {result.stderr}")
            continue

        # Execute notebook and convert to markdown
        ipynb_file = py_file.with_suffix(".ipynb")
        print(f"  Executing and converting to markdown...")
        result = subprocess.run(
            [
                "uv",
                "run",
                "jupyter",
                "nbconvert",
                "--to",
                "markdown",
                "--execute",
                str(ipynb_file),
                "--output-dir",
                str(py_file.parent),
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print(f"  Error executing/converting {ipynb_file.name}: {result.stderr}")
            continue

        print(f"  Successfully processed {py_file.name}")

    print("\nDone!")


if __name__ == "__main__":
    build_notebooks()
