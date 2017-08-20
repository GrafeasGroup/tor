#!/usr/bin/env python

import os
import codecs
from setuptools import (
    setup,
    find_packages,
)
from tor import __version__


def long_description():
    if not (os.path.isfile('README.rst') and os.access('README.rst', os.R_OK)):
        return ''

    with codecs.open('README.rst', encoding='utf8') as f:
        return f.read()


setup(
    name='tor',
    version=__version__,
    description='',
    long_description=long_description(),
    url='https://github.com/itsthejoker/transcribersofreddit',
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
    packages=find_packages(exclude=['test*', 'bin/*']),
    test_suite='test',
    entry_points={
        'console_scripts': [
            'tor-moderator = tor.main:main',
            'tor-apprentice = tor.ocr:main',
            'tor-archivist = tor.archiver:main',
        ],
    },
    install_requires=[
        'praw==4.4.0',
        'redis<3.0.0',
        'addict',
        'tesserocr',
        'wget',
        'sh',
        'bugsnag',
        'cython',  # WORKAROUND: 'tesserocr' only sometimes installs this dependency
    ]
)
