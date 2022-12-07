help:
	@echo 'make install:          Install package, hook, notebooks and gdslib'
	@echo 'make test:             Run tests with pytest'
	@echo 'make test-force:       Rebuilds regression test'

install:
	pip install -e .
	pip install pre-commit
	pre-commit install
	gf tool install

cov:
	pytest --cov=kfactory

venv:
	python3 -m venv env

lint:
	tox -e flake8

pylint:
	pylint kfactory

lintdocs:
	flake8 --select RST

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

.PHONY: build conda
