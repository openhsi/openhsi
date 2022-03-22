SRC = $(wildcard ./nbs/*.ipynb)

help:
	cat Makefile

all: openhsi docs

openhsi: $(SRC)
	nbdev_clean_nbs
	nbdev_build_lib
	touch openhsi

docs_serve: docs
	cd docs && bundle exec jekyll serve

docs: $(SRC)
	nbdev_build_docs
	touch docs
	cp assets/combo_logos.png docs/assets/images/company_logo.png
	cp assets/favicon.ico docs/assets/images/favicon.ico

test:
	nbdev_test_nbs --verbose True --flags test

release: pypi
	fastrelease_bump_version

conda_release:
	# usage : make conda_release version=0.x.x
	# copy from conda-forge,  after https://github.com/conda-forge/openhsi-feedstock is updated.
	anaconda copy conda-forge/openhsi/$(version) --to-owner openhsi

pypi: dist
	twine upload --repository pypi dist/*

dist: clean
	python setup.py sdist bdist_wheel

clean:
	rm -rf dist
