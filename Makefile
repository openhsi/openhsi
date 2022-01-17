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

release: pypi
		sleep 3
		fastrelease_conda_package --mambabuild --upload_user fastai
		fastrelease_bump_version
		nbdev_build_lib | tail

conda_release:
	fastrelease_conda_package --upload_user openhsi

pypi: dist
	twine upload --repository pypi dist/*

dist: clean
	python setup.py sdist bdist_wheel

clean:
	rm -rf dist
