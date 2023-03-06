project = "kfactory"
version = "0.4.5"
copyright = "2022"
# author = "kfactory"

# html_theme = "furo"
# html_theme = "sphinx_rtd_theme"
html_theme = "sphinx_book_theme"

source_suffix = {
    ".rst": "restructuredtext",
    ".txt": "markdown",
    ".md": "markdown",
}

html_static_path = ["_static"]
extensions = [
    "matplotlib.sphinxext.plot_directive",
    "myst_parser",
    "nbsphinx",
    "sphinx.ext.autodoc",
    "sphinx.ext.doctest",
    "sphinx.ext.mathjax",
    "sphinx.ext.napoleon",
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
    "sphinx_autodoc_typehints",
    "sphinx_click",
    "sphinx_markdown_tables",
    "sphinx_copybutton",
    "sphinxcontrib.autodoc_pydantic",
    "sphinx.ext.autosummary",
    "sphinx.ext.extlinks",
    "sphinxcontrib.video",
    "nbsphinx",
]

autodoc_member_order = "bysource"

templates_path = ["_templates"]
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    "**.ipynb_checkpoints",
    "build",
    "extra",
]

napoleon_use_param = True


language = "en"
myst_html_meta = {
    "description lang=en": "metadata description",
    "description lang=fr": "description des métadonnées",
    "keywords": "Sphinx, MyST",
    "property=og:locale": "en_US",
}

html_theme_options = {
    "path_to_docs": "docs",
    "repository_url": "https://github.com/gdsfactory/kfactory",
    "repository_branch": "master",
    "launch_buttons": {
        "binderhub_url": "https://mybinder.org/v2/gh/gdsfactory/kfactory/HEAD",
        "notebook_interface": "jupyterlab",
    },
    "use_edit_page_button": True,
    "use_issues_button": True,
    "use_repository_button": True,
    "use_download_button": True,
}

autodoc_pydantic_model_signature_prefix = "class"
autodoc_pydantic_field_signature_prefix = "attribute"
autodoc_pydantic_model_show_config_member = False
autodoc_pydantic_model_show_config_summary = False
autodoc_pydantic_model_show_validator_summary = False
autodoc_pydantic_model_show_validator_members = False


autodoc_default_options = {
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "exclude-members": "__weakref__",
    "inherited-members": True,
    "show-inheritance": True,
}
