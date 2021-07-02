.PHONY : develop clean clean_pyc lint-diff black test coverage

# Trick to get the args right after the target
ARGS = $(filter-out $@,$(MAKECMDGOALS))

clean:
	-python setup.py clean

clean_pyc:
	-find ./tests -name "*.py[co]" -exec rm {} \;
	-find ./lighttree -name "*.py[co]" -exec rm {} \;

lint-diff:
	git diff upstream/master --name-only -- "*.py" | xargs flake8

lint:
	python -m flake8 lighttree

black:
	black lighttree tests setup.py

develop:
	-python -m pip install -e ".[develop]"

test:
	-python -m pytest

coverage:
	-coverage run --source=./lighttree -m pytest
	coverage report