# Development setup with all extras
dev:
    uv sync --all-extras
    uv pip install -e . -U
    uv run pre-commit install

# Test environment setup
test-venv:
    uv sync --all-extras
    uv pip install -e .

# Zensical's tailored fork of mike for versioned docs deployment
MIKE := "mike @ git+https://github.com/squidfunk/mike.git"

# Clean documentation build
docs-clean:
    rm -rf site

# Pre-build docs source: convert jupytext .py to .md+.ipynb (with download
# button), generate mkdocstrings API reference stubs into docs/source-built/.
# Cached: re-runs only re-execute notebooks whose source hash changed.
docs-build-source python_version="3.14":
    uv run -p {{python_version}} --extra notebooks --with . python docs/scripts/build_docs_source.py

# Build documentation (zensical) from the pre-built source
docs python_version="3.14": docs-build-source
    uv run -p {{python_version}} --with-editable . --extra docs --with "{{MIKE}}" --isolated zensical build -f docs/zensical-built.yml

# Serve documentation locally (zensical) from the pre-built source
docs-serve python_version="3.14": docs-build-source
    uv run -p {{python_version}} --with-editable . --extra docs --with "{{MIKE}}" --isolated zensical serve -f docs/zensical-built.yml

# Deploy docs to gh-pages as the "dev" version (tracks main)
docs-deploy-dev python_version="3.14": docs-build-source
    uv run -p {{python_version}} --with . --extra docs --with "{{MIKE}}" --isolated mike deploy \
        --config-file docs/zensical-built.yml \
        --alias-type=redirect \
        --push \
        --update-aliases \
        dev

# Deploy docs to gh-pages as a tagged release version + set "latest" as default
docs-deploy-release version python_version="3.14": docs-build-source
    uv run -p {{python_version}} --with . --extra docs --with "{{MIKE}}" --isolated mike deploy \
        --config-file docs/zensical-built.yml \
        --alias-type=redirect \
        --push \
        --update-aliases \
        {{version}} latest
    uv run -p {{python_version}} --with . --extra docs --with "{{MIKE}}" --isolated mike set-default \
        --config-file docs/zensical-built.yml \
        --push \
        latest


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
