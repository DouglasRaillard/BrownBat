What is BrownBat ?
------------------
**BrownBat** is a pure Python library to create source code generators.
By source code generator, I mean a program which output is source code.
Its main features are:
 * Laziness everywhere: you can set every possible name or attribute after the object has been created and used, and 
   it will be taken into account when printed. This allows the generator to set the layout of the code, and for example set the names
   of the variables or functions later, when the correct name can be computed from another source of information.
   
 * Nifty operator overloading, making it quite easy to manipulate source code objects. 
 
It currently handles C langage, but adding new langages leveraging all the facilities given by the core should be easy.

Why would I want to generate some source code ?
-----------------------------------------------
Because it allows you to write custom tools to avoid repetitive or error prone tasks. A good example would be the generation 
of a serialization and deserialization routines for a C structure described in XML.
This can be quite easily accomplished with the help of this library and the standard Python library.

Supported langages
------------------
Currently, only C langage is supported.
That said, what makes this library interesting (laziness, operator overloading) is separated in a langage independent module (core), 
which should make it easy to add support for a new langage. A guide to write support code for new langages will be released in the next 
few months.


Installing
----------
**BrownBat** requires Python 3 to work correctly.
It can be installed from PyPI (Python package index)::

    > pip install brownbat
    
Alternatively, the development version can be retrieved on Github:
https://github.com/DouglasRaillard/BrownBat


How to use it ?
---------------
Documentation and guides will be made available in the next few month.
It will include examples and a guide to implement support for a new langage
(most of the hard work of operator overloading is inside a core module, which is langage independent).



License
-------
**BrownBat** is licensed under the GNU Lesser General Public License v3 or later (LGPLv3+) License.


Why BrownBat is named BrownBat ?
--------------------------------
Because those cute animals are very lazy (according to http://en.wikipedia.org/wiki/Little_brown_bat#Sleep, they can sleep up to 20h a day).
And this library is designed to be lazy at its very core.