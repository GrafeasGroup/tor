#!/usr/bin/env python

import os
import sys
import codecs
from setuptools import (
    setup,
    find_packages,
)
from setuptools.command.test import test as TestCommand

from tor import __version__


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to pytest")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = ''

    def run_tests(self):
        import shlex
        # import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(shlex.split(self.pytest_args))
        sys.exit(errno)


def long_description():
    if not (os.path.isfile('README.rst') and os.access('README.rst', os.R_OK)):
        return ''

    with codecs.open('README.rst', encoding='utf8') as f:
        return f.read()


testing_deps = [
    'pytest',
    'pytest-cov',
]
dev_helper_deps = [
    'better-exceptions',
]


setup(
    name='tor',
    version=__version__,
    description='A bot that handles moderating and scoring in /r/TranscribersOfReddit',
    long_description=long_description(),
    url='https://github.com/TranscribersOfReddit/TranscribersOfReddit',
    author='Joe Kaufeld',
    author_email='joe.kaufeld@gmail.com',
    license='MIT',
    classifiers=[
        'Development Status :: 1 - Planning',

        'Intended Audience :: End Users/Desktop',
        'Topic :: Communications :: BBS',

        'License :: OSI Approved :: MIT License',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='',
    packages=find_packages(exclude=['test', 'test.*', '*.test', '*.test.*']),
    test_suite='test',
    zip_safe=True,
    entry_points={
        'console_scripts': [
            'tor-moderator = tor.main:main',
        ],
    },
    tests_require=testing_deps,
    extras_require={
        'dev': testing_deps + dev_helper_deps,
    },
    cmdclass={'test': PyTest},
    install_requires=[
        'tor_core',
        'sh',
    ],
    dependency_links=[
        'git+https://github.com/TranscribersOfReddit/tor_core.git@master#egg=tor_core-0',
    ],
)
