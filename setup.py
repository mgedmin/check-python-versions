#!/usr/bin/env python
import ast
import os
import re

from setuptools import setup, find_packages


here = os.path.dirname(__file__)

with open(os.path.join(here, 'README.rst')) as f:
    long_description = f.read()

source_dir = os.path.join(here, 'src', 'check_python_versions')

metadata = {}
with open(os.path.join(source_dir, '__init__.py')) as f:
    rx = re.compile('(__version__|__author__|__url__|__licence__) = (.*)')
    for line in f:
        m = rx.match(line)
        if m:
            metadata[m.group(1)] = ast.literal_eval(m.group(2))
version = metadata['__version__']


setup(
    name='check-python-versions',
    version=version,
    author='Marius Gedminas',
    author_email='marius@gedmin.as',
    url='https://github.com/mgedmin/check-python-versions',
    description=(
        'Compare supported Python versions in setup.py vs tox.ini et al.'
    ),
    long_description=long_description,
    keywords=(
        'python packaging version checker linter setup.py tox travis appveyor'
    ),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
    license='GPL',
    python_requires=">=3.6",
    packages=find_packages('src'),
    package_dir={'': 'src'},
    entry_points={
        'console_scripts': [
            'check-python-versions = check_python_versions.cli:main',
        ],
    },
    install_requires=['pyyaml'],
    zip_safe=False,
)
