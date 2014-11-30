==================
BrownBat overview
==================

BrownBat is a package for creating source code generators. That means a Python program
which outputs for example C source code. Its API is orthogonal and designed to be handy when
informations from multiple configuration sources must be consolidated by the generator.


It may also be used in combination with tools like `Cog <http://nedbatchelder.com/code/cog/>`_
as it allows to easily build complex source code constructs.

A quick example showing BrownBat's capabilities:


>>> from brownbat import C
>>> printf_fun = C.Fun('printf')
>>> function = C.Fun('print_greetings')
>>> var = C.Var('char *string="hello world"', parent=function)
>>> function.append(printf_fun('"%s"',var))
>>> print(function.defi())
void print_greetings(void)
{
    char *string = "hello world";
    printf("%s", string);
}


The main features
-----------------

This library is built upon language independent base class. They implement what makes this library
interesting:

* You can use plain strings or objects implementing *__str__* everywhere
* When you use an object implementing *__str__*, this method will only be called
  when the string is actually needed, not before. This allows to construct an object,
  change some attributes later and then print it.
  
    That feature is really useful when you build some code by aggregating informations 
    from multiple sources. It allows you to build the skeleton, for example create a variable,
    and use it in the generated code, and then set its name later, when you come across the pieces
    of configuration informations that describes it. For example, you could prefix the name of global
    variables with a namespace prefix, to make it unique.

* In a lot of places, this library expects a special type of objects. For example, you should only store comments
  in an attribute that holds the comment of a snippet of code. However, this can be tedious to always explicitly 
  build such objects, because virtually every attribute has a special expectation of what should be stored inside 
  it. To alleviate this problem, some descriptor magic has been implemented: :class:`brownbat.core.EnsureNode`.
  This class makes sure that you give it the right kind of object, and if not, tries to build one out of what you 
  gave to it. For a comment attribute, an already built comment will be taken as is. But if you try to store a string,
  a comment will be built from it. That means two things:
  
  - Never expect to store an object in an attribute and get it back as you set it. It may have been transformed, and may
    not be the same anymore.
  - You do not need to exactly know what is going on, the correct behavior will usually be achieved with very little efforts
    from you. This makes the APIs highly orthogonal, and this is in the way of the least astonishment principle, because the 
    same classes are used everywhere and they all implement some nifty operator overloading. For example, it does not matter
    if your comment comes from a string or a comment object, you can append some text to it later in every cases.
  
* The base containers are language agnostic. That means that every languages supported has some common behavior regarding
  operator overloading and lazy calls to *__str__* methods.

  
Conventions used in this documentation 
--------------------------------------

The following convention is used through this documentation:

* The source code which is the output of the program (for example C source code) is
  referred to as the **generated code**.

* The source code of the Python script that creates an output is referred to as the
  **generator code**.
  
* The word **descriptor** is used to indicate that a particular attribute is an instance of
  a Python descriptor (class implementing *__get__* and *__set__*), and therefore is a class attribute.
  Nonetheless, it is intended to be used like an instance attribute, with a special behavior when read or written.
  
* A source code construct is a snippet of generated source code. For example, an *if* statement is a construct.

* A node is an object conforming to the API of :class:`brownbat.core.NodeABC`. Almost all classes of this library
  are nodes. An object not conforming to this API is called a non-node object.


Supported languages
-------------------

For now, only the C language is supported, but it is not that hard to implement another one.
C language support includes control constructs, functions, preprocessor and all commonly used source code constructs.