# Development setup with all extras
dev:
    uv sync --all-extras
    uv pip install -e .
    uv run pre-commit install

# Test environment setup
test-venv:
    uv sync --all-extras
    uv pip install -e .

# Clean documentation build
docs-clean:
    rm -rf site

# Build documentation
docs python_version="3.12":
    uv run -p {{python_version}} --extra docs --isolated mkdocs build -f docs/mkdocs.yml

# Serve documentation locally
docs-serve python_version="3.12":
    uv run -p {{python_version}} --extra docs --isolated mkdocs serve -f docs/mkdocs.yml

# Run tests (depends on init-submodule)
test python_version="3.12": init-submodule
    uv run -p {{python_version}} --extra ci --isolated pytest -s -n logical

# Run tests with minimum dependencies
test-min python_version="3.12":
    uv run -p {{python_version}} --extra ci --resolution lowest-direct --isolated pytest -s -n logical

# Run tests with coverage report (XML)
cov python_version="3.12":
    uv run -p {{python_version}} --extra ci --isolated pytest -n logical -s --cov=kfactory --cov-branch --cov-report=xml

# Run tests with coverage report (terminal)
dev-cov python_version="3.12":
    uv run -p {{python_version}} --extra ci --isolated pytest -n logical -s --cov=kfactory --cov-report=term-missing:skip-covered

# Run linting
lint:
    uv run ruff check .

# Run formatting
format:
    uv run ruff format .

# Run type checking
mypy:
    uv run dmypy run src/kfactory

# Run ty
ty:
    uv run ty check src/kfactory

# Submodule variable
SUBMOD := "tests/gdsfactory-yaml-pics"

# Initialize submodule
init-submodule:
    # init shallow
    git submodule update --init --depth 1 {{SUBMOD}}
    # ensure it tracks main on updates
    git submodule set-branch --branch main {{SUBMOD}}
    # restrict working tree to the yaml_pics folder
    git -C {{SUBMOD}} sparse-checkout init --cone
    git -C {{SUBMOD}} sparse-checkout set notebooks/yaml_pics

update-submodule:
    # pull latest main for the submodule, still shallow
    git submodule update --remote --depth 1 {{SUBMOD}}

clean-submodule:
    # remove only the checked-out files, keep the submodule entry
    git -C {{SUBMOD}} clean -xdf

gds-download:
	gh release download v0.6.0 -D gds/gds_ref/ --clobber
