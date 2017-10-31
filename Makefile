.PHONY: clean all test

all: test clean
	@true

clean:
	@# echo "Removing \`*.pyc', \`*.pyo', and \`__pycache__/'"
	@find . -regex '.+/[^/]+\.py[co]$$' -delete
	@find . -regex '.+/__pycache__$$' -exec rm -rf {} \; -prune

test: clean
	@python setup.py test
