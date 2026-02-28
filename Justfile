# Development setup with all extras
dev:
    uv sync --all-extras
    uv pip install -e . -U
    uv run pre-commit install

# Test environment setup
test-venv:
    uv sync --all-extras
    uv pip install -e .

# Clean documentation build
docs-clean:
    rm -rf site

# Build documentation
docs python_version="3.14":
    uv run -p {{python_version}} --with . --extra docs --isolated mkdocs build -f docs/mkdocs.yml

# Serve documentation locally
docs-serve python_version="3.14":
    uv run -p {{python_version}} --with . --extra docs --isolated mkdocs serve -f docs/mkdocs.yml

# Run tests (depends on init-submodule)
test python_version="3.14": init-submodule
    uv run -p {{python_version}} --with . --extra ci --isolated pytest -s -n logical

test-gdsfactory python_version="3.14": init-submodule
    # uv run -p {{python_version}} --no-sync --extra ci --with gdsfactory --with . --isolated pytest -s -vvvv -n logical tests/test_gdsfactory.py
    uv run -p {{python_version}} --extra ci --with gdsfactory --with jinja2 --with . --isolated pytest -s -vvvv tests/test_gdsfactory.py -x --pdb

# Run tests with minimum dependencies
test-min python_version="3.12": init-submodule
    uv run -p {{python_version}} --with . --extra ci --resolution lowest-direct --isolated pytest -s -n logical

# Run tests with coverage report (XML)
cov python_version="3.14": init-submodule
    uv run -p {{python_version}} --with . --extra ci --isolated pytest -n logical -s --cov=kfactory --cov-branch --cov-report=xml

# Run tests with coverage report (terminal)
dev-cov python_version="3.14": init-submodule
    uv run -p {{python_version}} --with . --extra ci --isolated pytest -n logical -s --cov=kfactory --cov-report=term-missing:skip-covered

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

# Submodule variables
YAML_PICS := "tests/gdsfactory-yaml-pics"
TEST_DATA := "tests/test_data"

init-submodule:
    git submodule update --init --recursive --depth 50

    # sparse checkout only after init
    git -C {{YAML_PICS}} sparse-checkout set --no-cone "/docs/notebooks/yaml_pics/"

# Update all submodules to latest main
update-submodule: update-yaml-pics update-test-data

# Update gdsfactory-yaml-pics submodule to latest main
update-yaml-pics:
    git submodule update --remote --depth 1 {{YAML_PICS}}

# Update test-data submodule to latest main
update-test-data:
    git submodule update --remote --depth 1 {{TEST_DATA}}

# Clean gdsfactory-yaml-pics submodule working tree
clean-submodule:
    git -C {{YAML_PICS}} clean -xdf

gds-download:
	gh release download v0.6.0 -D gds/gds_ref/ --clobber
