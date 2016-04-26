#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""A Python 3 client library for the Non Session Management protocol."""

from distutils.core import setup


setup(
    name="nsmclient",
    version="0.2b",
    py_modules=["nsmclient"],
    author="Nils Gey",
    author_email="ich@nilsgey.de",
    maintainer="Christopher Arndt",
    maintainer_email="chris@chrisarndt.de",
    url="https://github.com/SpotlightKid/pynsmclient",
    description=__doc__,
    license="GPLv3+",
    install_requires=["pyliblo"]
)
