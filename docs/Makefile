SPHINXOPTS    =
SPHINXBUILD   = sphinx-build
SPHINXPROJ    = kfactory
SOURCEDIR     = .
BUILDDIR      = build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile upload

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

convert:
	jupytext --set-formats ipynb,py notebooks/*.py

upload:
	mkdir -p site
	rsync -rv build/html/ site/kfactory

open:
	open build/html/index.html

see: html open
