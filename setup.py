import os
from setuptools import setup

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "BrownBat",
    version = "0.0b1",
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
