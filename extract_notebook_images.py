#!/usr/bin/env python3
"""Extract and save images from kfactory notebook files."""

from pathlib import Path
import re
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import kfactory as kf
from kfactory.utilities import as_png_data


def parse_jupytext_py(file_path: Path) -> list[dict]:
    """Parse a jupytext .py file and return cells."""
    content = file_path.read_text()

    # Split by cell markers
    cells = []
    current_cell = {"type": "code", "content": "", "is_markdown": False}

    lines = content.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]

        # Check for cell markers
        if line.strip() == "# %% [markdown]":
            # Save previous cell if it has content
            if current_cell["content"].strip():
                cells.append(current_cell)
            # Start new markdown cell
            current_cell = {"type": "markdown", "content": "", "is_markdown": True}
            i += 1
            continue
        elif line.strip() == "# %%":
            # Save previous cell if it has content
            if current_cell["content"].strip():
                cells.append(current_cell)
            # Start new code cell
            current_cell = {"type": "code", "content": "", "is_markdown": False}
            i += 1
            continue

        # Add line to current cell
        if current_cell["is_markdown"]:
            # Remove leading "# " from markdown lines
            if line.startswith("# "):
                current_cell["content"] += line[2:] + "\n"
            elif line.strip() == "#":
                current_cell["content"] += "\n"
        else:
            current_cell["content"] += line + "\n"

        i += 1

    # Add last cell
    if current_cell["content"].strip():
        cells.append(current_cell)

    return cells


def execute_and_extract_images(file_path: Path, output_dir: Path):
    """Execute a notebook and extract images from cells that create KCells."""
    print(f"\nProcessing {file_path.name}...")

    cells = parse_jupytext_py(file_path)

    # Create a namespace for execution
    namespace = {}

    # Track image index
    image_index = 0
    base_name = file_path.stem

    # Keep track of which cells have images
    cell_images = []

    for cell_idx, cell in enumerate(cells):
        if cell["type"] != "code":
            continue

        code = cell["content"].strip()
        if not code:
            continue

        # Skip cells that are just comments or imports in header
        if cell_idx < 5 and (code.startswith("# ---") or "jupyter:" in code):
            continue

        try:
            # Execute the cell
            exec(code, namespace)

            # Check if the cell has output that should be visualized
            # Look for .show(), .plot(), or cells ending with a variable that might be a KCell
            has_show = ".show()" in code
            has_plot = ".plot()" in code

            # Also check if the last line is a simple variable reference (would show output)
            lines = [l.strip() for l in code.split("\n") if l.strip() and not l.strip().startswith("#")]
            if lines:
                last_line = lines[-1]
                # Check if last line is a simple variable reference (no assignment, function call with return, etc)
                if (
                    not "=" in last_line
                    and not last_line.startswith("def ")
                    and not last_line.startswith("class ")
                    and not last_line.startswith("import ")
                    and not last_line.startswith("from ")
                    and re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', last_line)
                ):
                    # This might be a cell output
                    has_show = True

            # If this cell should show output, try to extract KCells
            if has_show or has_plot:
                # Look for KCell objects in the namespace
                for var_name in list(namespace.keys()):
                    obj = namespace[var_name]

                    # Check if it's a KCell
                    if hasattr(obj, 'kcl') and hasattr(obj, 'kdb_cell'):
                        try:
                            # Generate PNG
                            png_data = as_png_data(obj)

                            # Save PNG
                            output_file = output_dir / f"{base_name}_{image_index}.png"
                            output_file.write_bytes(png_data)
                            print(f"  Saved: {output_file.name} (from cell {cell_idx}, var '{var_name}')")

                            cell_images.append({
                                "cell_idx": cell_idx,
                                "image_file": output_file.name,
                                "var_name": var_name
                            })

                            image_index += 1
                        except Exception as e:
                            print(f"  Warning: Could not generate image for {var_name}: {e}")

        except Exception as e:
            print(f"  Warning: Error executing cell {cell_idx}: {e}")
            # Continue with next cell
            continue

    print(f"  Total images extracted: {image_index}")
    return cell_images


def main():
    """Main function."""
    # Setup paths
    notebooks_dir = Path(__file__).parent / "docs" / "source" / "notebooks"
    output_dir = notebooks_dir

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process all .py notebook files
    py_files = sorted(notebooks_dir.glob("*.py"))

    if not py_files:
        print("No .py files found in notebooks directory")
        return

    print(f"Found {len(py_files)} notebook files")

    for py_file in py_files:
        try:
            execute_and_extract_images(py_file, output_dir)
        except Exception as e:
            print(f"Error processing {py_file.name}: {e}")
            import traceback
            traceback.print_exc()

    print("\nDone!")


if __name__ == "__main__":
    main()
