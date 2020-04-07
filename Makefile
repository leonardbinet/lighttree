.PHONY : develop clean clean_pyc lint-diff black test coverage

clean:
	-python setup.py clean

clean_pyc:
	-find ./tests -name "*.py[co]" -exec rm {} \;
	-find ./lighttree -name "*.py[co]" -exec rm {} \;

lint-diff:
	git diff upstream/master --name-only -- "*.py" | xargs flake8

black:
	black lighttree tests setup.py

develop:
	-python -m pip install -e .

test:
	-python -m unittest

coverage:
	-coverage run --source=./lighttree -m unittest
	coverage report
