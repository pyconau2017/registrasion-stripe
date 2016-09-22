#!/usr/bin/env python
import os
from setuptools import setup, find_packages

import registripe


def read_file(filename):
    """Read a file into a string."""
    path = os.path.abspath(os.path.dirname(__file__))
    filepath = os.path.join(path, filename)
    try:
        return open(filepath).read()
    except IOError:
        return ''

setup(
    name="registrasion-stripe",
    author="Christopher Neugebauer",
    author_email="_@chrisjrn.com",
    version=registripe.__version__,
    description="Stripe-based payments for the Registrasion conference registration package.",
    url="http://github.com/chrisjrn/registrasion-stripe/",
    packages=find_packages(),
    include_package_data=True,
    classifiers=(
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "License :: OSI Approved :: Apache Software License",
    ),
    install_requires=read_file("requirements.txt").splitlines(),
)
