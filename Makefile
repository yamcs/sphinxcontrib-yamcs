.PHONY: clean build deploy

clean:
	rm -rf build dist *.egg-info

build:
	python -m build

deploy: clean build
	twine upload -r pypi dist/*
