==============
Core concepts
==============


As stated in the overview, this library stands upon some language independent classes.
They implement some features that you will find everywhere. All the constructor parameters
of base class *must* be used as keywords arguments, the order of positinal arguments 
is not guaranteed except in the leaf classes in the inheritance hierarchy.

Nodes
-----

The basic element is a node. Every classes that represent source code constructs are 
referred as nodes, and they are used to build something like a tree of nodes.
Every node should be printable in two contexts:

* the inline context, which is mainly used when printed inside a token container.
* the freestanding context, which is used when printed inside a node container.

For example, a variable object is printed as its name in an inline context, and as the variable's declaration
in a freestanding context. 

  
Containers
----------

There are basically two types of node containers:

* **node containers** contains node that should be displayed independently inside the container.
  
* **token containers** are actually used as a lazy replacement for strings.


Nodes containers
................

This kind of container is the base of all statements that contain multiple line of codes: control statements, functions, etc.
They are all child class of :class:`brownbat.core.NodeContainerBase`. They provide the following interface:

* a *node_list* constructor keyword argument: this is the intial list of nodes. This can be any iterable, or even a single object, it will be 
  converted into a list in the constructor.  
* they are mutable sequence object (:class:`collections.abc.MutableSequence`). When given a non-node object, they usually try to build
  a node out of it.
* they are not unrolled to a plain list when given to another node container. That means that if you store a node container inside another,
  you will be able to add some nodes to the inner node container later, and they will be printed when printing the outer container.

They print their nodes in a freestanding context.
  
  
Token containers
................

This kind of container is basically a replacement for plain strings. They are used as identifiers, expressions and so on.
When printed, they will turn their tokens into a string, and concatenate them. If the token is a node, it will be printed in
an inline context, and *str()* builtin will be called on non-node objects.
This allows to store anything inside it, and it will be lazily evaluated when printed. One could create a special class for
variable names, to allow special naming conventions formatting. This class would only need to implement *__str__*, and then
it could be used inside any token container.

.. note:: :class:`brownbat.core.TokenListBase` child class are used in conjunction with :class:`brownbat.core.EnsureNode`
          in nearly every attribute that need to store an identifier of some sort (variable names), or expressions (*if*
          statement conditions)


