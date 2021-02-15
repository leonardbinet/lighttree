#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

__version__ = "1.1.0"


setup(
    name="lighttree",
    version=__version__,
    url="https://github.com/leonardbinet/lighttree",
    author="Léonard Binet",
    author_email="leonardbinet@gmail.com",
    license="MIT",
    packages=["lighttree"],
    keywords=["tree", "interactive"],
    install_requires=["future"],
)
