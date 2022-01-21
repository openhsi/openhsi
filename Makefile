SRC = $(wildcard ./nbs/*.ipynb)

all: openhsi docs

help:
	cat Makefile

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

release: pypi conda_release
	fastrelease_bump_version

changelog:
	fastrelease_changelog

conda_release:
	fastrelease_conda_package --do_build false && \
	cd conda && \
	conda build --no-anaconda-upload --output-folder build openhsi && \
	anaconda upload build/noarch/{name}-{ver}-*.tar.bz2
	cd ..

pypi: dist
	echo "twine upload --repository pypi dist/*"

dist: clean
	python setup.py sdist bdist_wheel

clean:
	rm -rf dist
