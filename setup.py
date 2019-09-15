#!/usr/bin/env python

import codecs
import os

from setuptools import find_packages, setup

from tor import __version__


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
    url='https://github.com/GrafeasGroup/tor',
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
    package_data={
        '': ['commands.json'],
        'tor.strings': ['*.yml', '*.yaml'],
    },
    zip_safe=True,
    entry_points={
        'console_scripts': [
            'tor-moderator = tor.cli.main:main',
            'tor-flair-backup = tor.cli.backup:main',
        ],
    },
    extras_require={
        'dev': testing_deps + dev_helper_deps,
    },
    tests_require=testing_deps,
    install_requires=[
        'praw==5.0.1',
        'redis<3.0.0',
        'sh',
        'cherrypy',
        'bugsnag',
        'PyYAML',
        'requests',
        'slackclient<2.0.0'
    ],
)
