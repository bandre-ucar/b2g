#! /usr/bin/env python

#
# based on template example from:
# https://github.com/hcarvalhoalves/python-package-template
#

from setuptools import setup, find_packages

import sys
import os

BASE_LOCATION = os.path.abspath(os.path.dirname(__file__))

VERSION_FILE = 'VERSION'
REQUIRES_FILE = 'requirements.txt'
DEPENDENCIES_FILE = 'requirements_links.txt'


def readfile(filename, func):
    try:
        with open(os.path.join(BASE_LOCATION, filename)) as f:
            data = func(f)
    except (IOError, IndexError):
        sys.stderr.write(u"""
Unable to open file: {0}
For development run:
    make develop
    setup.py develop
To build a valid release, run:
    make release
""".format(filename))
        sys.exit(1)
    return data


def get_version():
    return readfile(VERSION_FILE, lambda f: f.read().strip())


def get_requires():
    return readfile(REQUIRES_FILE, lambda f: f.read().strip())


def get_dependencies():
    return readfile(DEPENDENCIES_FILE, lambda f: f.read().strip())

setup(
    name="bugzilla_to_github",
    author="Ben Andre",
    author_email="andre@ucar.edu",
    packages=['b2g'],
    version=get_version(),
    scripts=['b2g/b2g.py',
             ],

    install_requires=get_requires(),
    #dependency_links=get_dependencies(),
    include_package_data=True,
    zip_safe=True,
    test_suite="b2g.tests",
    description="Custom utility to migrate bugzilla issues to github issues..",
    use_2to3=True,
)
