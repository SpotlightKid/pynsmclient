#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
    description="""\
Python nsmclient is a convenience wrapper around liblo and the NSM-OSC protocol
to implement Non Session Management support easily in your own Python programs.
""",
    license="GPLv3+"
)
