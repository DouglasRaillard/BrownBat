#! /usr/bin/env python3

import os
from setuptools import setup

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "BrownBat",
    version = "0.0b2",
    author = "Douglas RAILLARD",
    author_email = "douglas.raillard.github@gmail.com",
    description = "A lazy source code generation library",
    long_description=read('README.rst'),
    license = "GNU Lesser General Public License v3 or later (LGPLv3+)",
    keywords = "source generation lazy code meta",
    url = "https://github.com/DouglasRaillard/BrownBat",
    packages = ['brownbat'],
    classifiers=[
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Software Development :: Code Generators",        
    ],
) 
