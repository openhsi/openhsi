SRC = $(wildcard ./*.ipynb)

all: openhsi docs

openhsi: $(SRC)
	nbdev_build_lib
	touch openhsi

docs_serve: docs
	cd docs && bundle exec jekyll serve

docs: $(SRC)
	nbdev_build_docs
	touch docs
	cp assets/combo_logos.png docs/_site/assets/images/company_logo.png
	cp assets/favicon.ico docs/_site/assets/images/favicon.ico

test:
	nbdev_test_nbs --verbose --flags test

release: pypi
	nbdev_bump_version

pypi: dist
	twine upload --repository pypi dist/*

dist: clean
	python setup.py sdist bdist_wheel

clean:
	rm -rf dist
