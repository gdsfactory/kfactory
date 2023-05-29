

help:
	@echo 'make install:                                Install package, hook, notebooks and gdslib'
	@echo 'make test:                                   Run tests with pytest'
	@echo 'make test-force:                             Rebuilds regression test'
	@echo 'make docs:                                   Build the docs and place them in ./site'
	@echo 'make docs-serve:                             mkdocs serve the docs'
	@echo 'make release-dr VERSION=MAJOR.MINOR.PATCH:   Dry run for new release with version number v${MAJOR}.${MINOR}.${PATCH}'
	@echo 'make release VERSION=MAJOR.MINOR.PATCH:      Dry run for new release with version number v${MAJOR}.${MINOR}.${PATCH}'

install:
	pip install -e .[docs,dev]
	pre-commit install

docs-clean:
	rm -rf site

docs:
	mkdocs build -f docs/mkdocs.yml

docs-serve:
	mkdocs serve -f docs/mkdocs.yml

test:
	pytest -s

cov:
	pytest --cov=kfactory

venv:
	python3 -m venv env

lint:
	flake8 .

pylint:
	pylint kfactory

pydocstyle:
	pydocstyle kfactory

doc8:
	doc8 docs/

autopep8:
	autopep8 --in-place --aggressive --aggressive **/*.py

codestyle:
	pycodestyle --max-line-length=88

git-rm-merged:
	git branch -D `git branch --merged | grep -v \* | xargs`

update-pre:
	pre-commit autoupdate --bleeding-edge

release:
	tbump ${VERSION}
release-dr:
	tbump --dry-run ${VERSION}

gds-upload:
	gh release upload v0.6.0 gds/gds_ref/*.gds --clobber

gds-download:
	gh release download v0.6.0 -D gds/gds_ref/ --clobber

.PHONY: build docs
