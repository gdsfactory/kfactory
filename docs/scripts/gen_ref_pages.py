"""Generate the code reference pages."""
# This script automatically generates the API reference documentation for a Python project.
# It scans the source code, creates a corresponding Markdown file for each Python module,
# and builds a navigation menu to link them all together, preparing the structure for a documentation website using MkDocs.

# First the script scans for Python files via for path in sorted(Path("src").rglob("*.py")).
# It then prepares three paths for each Python file that was found:
# module_path: The Python import path.
# doc_path: The corresponding path for the documentation file.
# full_doc_path: The final destination where the Markdown file will be created.
# Then it works with special files:
# It intelligently handles __init__.py files, treating them as the main page for a package (saving them as index.md).
# Also completely skips __main__.py files, as they are meant for execution, not for API documentation.
# Furthermore, it will generate documentation files:
# with mkdocs_gen_files.open(full_doc_path, "w") as fd:: The script opens a new Markdown file at the destination path.
# fd.write(f"::: {ident}"): This is the most important step. It writes a single line to the file, like ::: my_package.my_module.
# This is a special instruction for the mkdocstrings plugin, telling it to automatically find that Python module,
# inspect its functions and classes, and render their docstrings as documentation on that page.
# Lastly, it builds the navigation menu:
# nav[parts] = doc_path.as_posix(): As it processes each file, the script adds an entry to a navigation object (nav).
# It uses the directory structure to create a nested navigation menu.
# nav_file.writelines(nav.build_literate_nav()): After the loop is finished, it writes the complete, structured navigation menu to a SUMMARY.md file.
# MkDocs uses this file to build the site's sidebar.

from pathlib import Path
import klayout
import mkdocs_gen_files

nav = mkdocs_gen_files.Nav()


for path in sorted(Path("src").rglob("*.py")):  #
    module_path = path.relative_to("src").with_suffix("")  #
    doc_path = path.relative_to("src").with_suffix(".md")  #
    full_doc_path = Path("reference", doc_path)  #

    parts = list(module_path.parts)

    if parts[-1] == "__init__":  #
        parts = parts[:-1]
        doc_path = doc_path.with_name("index.md")
        full_doc_path = full_doc_path.with_name("index.md")
    elif parts[-1] == "__main__":
        continue

    nav[parts] = doc_path.as_posix()  #

    with mkdocs_gen_files.open(full_doc_path, "w") as fd:
        ident = ".".join(parts)
        fd.write(f"::: {ident}")

    mkdocs_gen_files.set_edit_path(full_doc_path, path)

    with mkdocs_gen_files.open("reference/SUMMARY.md", "w") as nav_file:  #
        nav_file.writelines(nav.build_literate_nav())  #
