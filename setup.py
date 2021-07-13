#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

__version__ = "1.1.3"

develop_requires = [
    "pre-commit",
    "black",
    "flake8",
    "mock",
    "coverage",
    "pytest",
    "mypy",
    "twine",
]

setup(
    name="lighttree",
    version=__version__,
    url="https://github.com/leonardbinet/lighttree",
    author="Léonard Binet",
    author_email="leonardbinet@gmail.com",
    license="MIT",
    packages=["lighttree"],
    package_data={
        "lighttree": ["py.typed"],
    },
    keywords=["tree", "interactive"],
    extras_require={"develop": develop_requires},
    tests_require=develop_requires,
)
