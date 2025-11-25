#!/usr/bin/env python3
"""Convert kfactory notebooks to markdown with images."""

from pathlib import Path
import re
import sys
import ast

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import kfactory as kf
from kfactory.utilities import as_png_data


def parse_jupytext_py(file_path: Path) -> list[dict]:
    """Parse a jupytext .py file and return cells with metadata."""
    content = file_path.read_text()

    cells = []
    current_cell = {"type": "code", "content": "", "is_markdown": False, "lines": []}

    lines = content.split("\n")
    i = 0
    start_line = 0

    while i < len(lines):
        line = lines[i]

        # Check for cell markers
        if line.strip() == "# %% [markdown]":
            # Save previous cell if it has content
            if current_cell["content"].strip():
                cells.append(current_cell)
            # Start new markdown cell
            start_line = i
            current_cell = {
                "type": "markdown",
                "content": "",
                "is_markdown": True,
                "lines": [],
                "start_line": start_line,
            }
            i += 1
            continue
        elif line.strip() == "# %%":
            # Save previous cell if it has content
            if current_cell["content"].strip():
                cells.append(current_cell)
            # Start new code cell
            start_line = i
            current_cell = {
                "type": "code",
                "content": "",
                "is_markdown": False,
                "lines": [],
                "start_line": start_line,
            }
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

        current_cell["lines"].append(line)
        i += 1

    # Add last cell
    if current_cell["content"].strip():
        cells.append(current_cell)

    return cells


def should_output_image(code: str) -> tuple[bool, str | None]:
    """Determine if a code cell should output an image and what variable to use."""
    code = code.strip()
    if not code:
        return False, None

    # Check for explicit show/plot calls
    has_show = ".show()" in code
    has_plot = ".plot()" in code

    if has_show or has_plot:
        # Try to find what variable is being shown/plotted
        lines = [l.strip() for l in code.split("\n") if l.strip() and not l.strip().startswith("#")]
        for line in reversed(lines):
            if ".show()" in line or ".plot()" in line:
                # Extract variable name before the method call
                match = re.search(r"(\w+)\.(show|plot)\(\)", line)
                if match:
                    return True, match.group(1)
        return True, None

    # Check if last line is a simple variable reference (implicit output)
    lines = [l.strip() for l in code.split("\n") if l.strip() and not l.strip().startswith("#")]
    if lines:
        last_line = lines[-1]
        # Check if last line is a simple variable reference
        if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", last_line):
            return True, last_line

    return False, None


def execute_and_generate_markdown(file_path: Path, output_dir: Path, images_dir: Path):
    """Execute a notebook and generate markdown with embedded images."""
    print(f"\nProcessing {file_path.name}...")

    cells = parse_jupytext_py(file_path)
    base_name = file_path.stem

    # Create a namespace for execution
    namespace = {}

    # Track image index
    image_index = 0

    # Build markdown output
    markdown_lines = []

    for cell_idx, cell in enumerate(cells):
        if cell["type"] == "markdown":
            # Add markdown content directly
            markdown_lines.append(cell["content"])
            continue

        # Code cell
        code = cell["content"].strip()
        if not code:
            continue

        # Skip header cells
        if cell_idx < 5 and (code.startswith("# ---") or "jupyter:" in code):
            continue

        # Add code block to markdown
        markdown_lines.append("```python")
        markdown_lines.append(code)
        markdown_lines.append("```")
        markdown_lines.append("")

        # Execute the cell
        try:
            exec(code, namespace)

            # Check if this cell should output an image
            should_show, var_name = should_output_image(code)

            if should_show:
                # Try to get the KCell to visualize
                kcell_to_save = None

                if var_name and var_name in namespace:
                    obj = namespace[var_name]
                    if hasattr(obj, "kcl") and hasattr(obj, "kdb_cell"):
                        kcell_to_save = obj
                else:
                    # Look for the most recently created KCell
                    # Prefer variables with short names (c, wg, etc.) as they're typically the main output
                    candidates = []
                    for vname in namespace:
                        obj = namespace[vname]
                        if hasattr(obj, "kcl") and hasattr(obj, "kdb_cell"):
                            # Prioritize short variable names
                            priority = len(vname)
                            candidates.append((priority, vname, obj))

                    if candidates:
                        candidates.sort()
                        kcell_to_save = candidates[0][2]
                        var_name = candidates[0][1]

                if kcell_to_save:
                    try:
                        # Generate PNG
                        png_data = as_png_data(kcell_to_save)

                        # Save PNG
                        image_filename = f"{base_name}_{image_index}.png"
                        image_path = images_dir / image_filename
                        image_path.write_bytes(png_data)

                        print(f"  Saved: {image_filename} (cell {cell_idx}, var '{var_name}')")

                        # Add image reference to markdown
                        markdown_lines.append(f"![{var_name}]({image_filename})")
                        markdown_lines.append("")

                        image_index += 1
                    except Exception as e:
                        print(f"  Warning: Could not generate image for cell {cell_idx}: {e}")

        except Exception as e:
            print(f"  Warning: Error executing cell {cell_idx}: {e}")
            # Continue with next cell
            continue

    # Write markdown file
    md_filename = f"{base_name}.md"
    md_path = output_dir / md_filename
    md_path.write_text("\n".join(markdown_lines))
    print(f"  Created: {md_filename} with {image_index} images")

    return image_index


def main():
    """Main function."""
    # Setup paths
    notebooks_dir = Path(__file__).parent / "docs" / "source" / "notebooks"
    output_dir = notebooks_dir
    images_dir = notebooks_dir

    # Ensure directories exist
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    # Remove old PNG files
    print("Cleaning up old PNG files...")
    for png_file in images_dir.glob("*.png"):
        png_file.unlink()
        print(f"  Removed: {png_file.name}")

    # Process all .py notebook files
    py_files = sorted(notebooks_dir.glob("*.py"))

    if not py_files:
        print("No .py files found in notebooks directory")
        return

    print(f"\nFound {len(py_files)} notebook files")

    total_images = 0
    for py_file in py_files:
        try:
            count = execute_and_generate_markdown(py_file, output_dir, images_dir)
            total_images += count
        except Exception as e:
            print(f"Error processing {py_file.name}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\nDone! Generated {len(py_files)} markdown files with {total_images} total images")


if __name__ == "__main__":
    main()
