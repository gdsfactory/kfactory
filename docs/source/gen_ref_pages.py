"""Generate the code reference pages."""

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

# KLayout part, doesn't work properly 2023-05-22
base_path_klayout = Path("klayout")
for path in sorted(Path(klayout.__path__[0]).rglob("*.pyi")):  #
    module_path = base_path_klayout / path.relative_to(path.parent).with_suffix("")  #
    doc_path = base_path_klayout / path.relative_to(path.parent).with_suffix(".md")  #
    print(f"{module_path=}")
    print(f"{doc_path=}")
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
