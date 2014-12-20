
# Copyright 2014 Douglas RAILLARD
#
# This file is part of BrownBat.
#
# BrownBat is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# BrownBat is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public License
# along with BrownBat. If not, see <http://www.gnu.org/licenses/>.

"""
.. moduleauthor:: Douglas RAILLARD <douglas.raillard.github@gmail.com>

This module mostly provides base classes intended to be subclassed for building
langage specific source code generation libraries.

They implement functionnalities related to operators overloading that can be used in any langage.
Every class representing source code constructs are known as node.
The following helpers functions are provided:

* :func:`listify`: create a list from an iterable or a single element.
* :func:`format_string`: format a string according to the given convention (camel case, upper case, etc.).
* :func:`strip_starting_blank_lines`: strip the blank lines at the beginning of a multiline string.

The following classes are provided:

* :class:`Indentation`: manage the indentation level in the code generator.
* :class:`NonIterable`: inheriting that class allows a class which can be considered as iterable to be considered as a non iterable by :func:`listify`.
* :class:`NodeMeta`: metaclass of all class representing some source code constructs.
* :class:`NodeABC`: abstract base class of all class representing some source code constructs.
* :class:`NodeBase`: base class of almost all class representing some source code constructs.
* :class:`NodeAttrProxy`: proxy class that forwards the calls to the :class:`NodeABC` API to an attribute which is itself a :class:`NodeABC`. It implements composition.
* :class:`EnsureNode`: descriptor used to build attributes that guarantee that they contain an instance of NodeABC.
* :class:`DelegateAttribute`: descriptor used to delegate an attribute to another instance which has the given attribute name.
* :class:`NodeViewBase`: base class for class representing a view of another node (for example a variable declaration is a view of a variable).
* :class:`PhantomNode`: class which can be used as an empty placeholder when a node is required.
* :class:`NodeContainerBase`: base class for node containers. It mostly implements operator overloading.
* :class:`TokenListABC`: abstract base class for token lists. This is a node that can contain a list of any object that can be used as a string, and concatenate them when printed.
* :class:`DelegatedTokenListBase`: base class for a token list that uses a specific attribute to really hold the token list instance (thus implementing composition instead of inheritance).
* :class:`TokenListBase`: base class for a token list.
* :class:`IndentedTokenListBase`: base class for a token list which indents it content when printed.
* :class:`IndentedDelegatedTokenListBase`: mix of :class:`IndentedTokenListBase` and :class:`DelegatedTokenListBase`.
* :class:`BacktraceBase`: base class for special token list that output a simplified backtrace of Python code that was used to build the instance. Useful when trying to debug the code generator.

"""
    

import collections
import numbers
import abc
import inspect
import copy 
import functools
import os


def listify(iterable_or_single_elem):
    """Create a list out of:
    
    * an iterable object: the result will be like ``list(iterable_or_single_elem)``
    * a object which cannot be iterated over: return a list with only one item (just the object)
    * an object which is iterable, but also a subclass of :class:`NonIterable`: 
      return a list with just the object, as if it was not iterable.
    """
    if iterable_or_single_elem is None:
        return []
    # We exclude iterables such as strings or NonIterable (StmtContainer for example)
    # because we want to keep them as one object and not split them
    if isinstance(iterable_or_single_elem, collections.Iterable) \
        and not isinstance(iterable_or_single_elem, (str, NonIterable)):
        return list(iterable_or_single_elem)
    else:
        return [iterable_or_single_elem]

def format_string(string, style, separator="_"):
    """ Format a string according to a convention.
    
    It is can be used to write identfiers name in a unified format before applying a naming convention.
    
    :param string: the string to be modified. It must be in a format where the word sperator is always the same.
    :param style: the convention. It can be one of:
    
                  * UpperCamelCase
                  * lowerCamelCase
                  * lower_underscore_case
                  * UPPER_UNDERSCORE_CASE
    :param separator: the word separator used to split the words appart before applying the convention.
                      It defaults to '_'.
    """
    if isinstance(string, collections.Iterable) and not isinstance(string, (str, NonIterable)):
        token_list = string
    else:
        token_list = str(string).split(separator)
        # If there is only one token in the list and in case it is an empty
        # string, we dont want to replace it with a _
        if len(token_list) != 1:
            for i, token in enumerate(token_list):
                if not token:
                    token_list[i] = separator

    if style == "UpperCamelCase":
        return "".join(token.capitalize() for token in token_list)

    if style == "lowerCamelCase":
        first_word = token_list[0].lower()
        remain_list = token_list[1:]
        return first_word+"".join(token.capitalize() for token in remain_list)

    if style == "lower_underscore_case":
        return "_".join(token.lower() for token in token_list)

    if style == "UPPER_UNDERSCORE_CASE":
        return "_".join(token.upper() for token in token_list)

def strip_starting_blank_lines(snippet):
    """Strip blank lines at the beginning of a multiline string."""

    last_new_line_pos = 0
    for position, char in enumerate(snippet):
        if char=='\n':
            last_new_line_pos = position
        elif char!='\t' and char!=' ' and char!='\v':
            break
    # Only keep one new line at the beginning, to avoid multiple blank lines
    return snippet[last_new_line_pos:]

class Indentation:
    """This class manages the indentation in the source code output.
    
    Instances can be used be printed to give the string to put at the beginning of a new indented line.
    
    >>> idt = Indentation()
    >>> idt.indent()
    >>> print('*'+str(idt)+'indented Hello World')
        indented Hello World
    """
    
    # Default indentation style (4 spaces)
    indentation_string = '    '
    
    @classmethod
    def make_idt(cls, idt):
        """Create a new indentation instance if *idt* is None,
           or return *idt* if it is already an :class:`Indentation` instance.
        """
        if idt is None:
            idt = cls()
        elif isinstance(idt, numbers.Integral):
            idt = cls(idt)
        elif isinstance(idt, str):
            idt = cls(indentator=idt) 
        return idt
        
    
    def __init__(self, level=0, indentator=None):
        """
        :param level: the initial indentation level
        :type level: int
        :param indentator: the string used to display indentation.
                           It defaults to the class attribute *indentation_string* which is four spaces.
        """
        self.indentation_level = level
        # If an indentation is string is given, override the classwide default with
        # an instance-local string
        if indentator is not None:
            self.indentation_string = indentator

    def indent(self, level=1):
        """Increase the indentation level by *level* levels."""
        self.indentation_level += level

    def dedent(self, level=1):
        """Decrease the indentation level by *level* levels."""
        self.indentation_level -= level

    def __str__(self):
        """Return the string to be used at the beginning of a line to display the indentation."""
        return self.indentation_string * self.indentation_level
    

class NonIterable:
    """ Inheriting from this class will prevent a class to be considered as
        :class:`collections.Iterable` by :func:`listify`. 
    """
    pass

class NodeMeta(abc.ABCMeta):
    """Meta class used for every node, i.e. every class representing source code constructs.
    
    Currently, it only does a bit of black magic on :meth:`NodeABC.inline_str` and :meth:`NodeABC.self_inline_str` methods:
    it creates a wrapper around them that calls *inline_str_filter* if it exists on their return string, to
    let the user apply some naming convention at the latest stage.
    """
    def __new__(meta, name, bases, dct):
        # Add automatic 'inheritance' for __format_string class attribute
        attr_name = '_'+name+'__format_string'
        if bases and not attr_name in dct:
            try:
                dct[attr_name] = bases[0].__dict__['_'+bases[0].__name__+'__format_string']
            except KeyError:
                pass
        
        # Wrap inline_str function to allow automatic filtering on its output
        def make_wrapper(wrapped_fun):
            @functools.wraps(wrapped_fun)
            def wrapper_fun(self, *args, **kwargs):
                result = wrapped_fun(self, *args, **kwargs)
                try:
                    filter_fun = self.inline_str_filter
                except AttributeError:
                    # Just return the string as is, no filter hook is installed
                    return result
                else:
                    # Call the filter on the resulting string
                    return filter_fun(result)

            return wrapper_fun
        
        for stringify_fun_name in ['inline_str', 'self_inline_str']:
            if stringify_fun_name in dct:
                wrapped_fun = dct[stringify_fun_name]
                dct[stringify_fun_name] = make_wrapper(wrapped_fun)
        
        return super().__new__(meta, name, bases, dct)
        
class NodeABC(metaclass=NodeMeta):
    """This class is an Abstract Base Class describing the most basic API evey node should conform to."""
    __format_string = ''
    
    @abc.abstractmethod
    def inline_str(self, idt=None):
        """This function is called to print the content of the node in an inline context.
        
        This can be for example when the node is printed inside an expression.
        This function should not try to print a preceding new line or indentation string.
        """
        
        pass
    @abc.abstractmethod
    def freestanding_str(self, idt=None):
        """This function is called to print the content of the node in a freestanding context.
        
        This can be for example when the node is printed in directly in the source file.
        This function should print the preceding new line and indentation if the source code constructs
        requires it.
        """
        pass
    
    @abc.abstractmethod
    def adopt_node(self, child):
        pass

class NodeAttrProxy(NodeABC):
    """This class is a proxy that redirects calls to the :class:`NodeABC` API to an attribute.
    
    It creates stubs that allows transparent composition.
    """
    def __init__(self, obj, attr_name):
        self.obj = obj
        self.attr_name = attr_name
    
    def inline_str(self, idt=None):
        return getattr(self.obj, self.attr_name).inline_str(idt)
    
    def freestanding_str(self, idt=None):
        return getattr(self.obj, self.attr_name).freestanding_str(idt)
    
    def adopt_node(self, child):
        return getattr(self.obj, self.attr_name).adopt_node(child)

class EnsureNode:
    """This class is a descriptor that makes sure that the attribute that uses it holds a reference
    to an instance of one of the classes given in *node_classinfo*.
    
    When set, this descriptor check if the given object is indeed an instance of *node_classinfo* classes.
    If not, it calls *node_factory* to build an object and store its return value. Therefore,
    the content of the attribute using this descriptor is always some instance of the classes
    contained in *node_classinfo*.
    
    .. note:: The *node_classinfo* always contains the class :class:`NodeABC`.
    """
    def __init__(self, storage_attr_name, node_factory, node_classinfo=()):
        """
        :param storage_attr_name: the underlying attribute used to store the object.
        :param node_factory: the factory called when someone tries to store a non :class:`NodeABC` inside the attribute.
        :param node_classinfo: this is a tuple that containes classes.
                               The value stored in the attribute is checked against this tuple using :func:`isinstance` to
                               determine if the factory should be used. This always contains at least :class:`NodeABC`
        """
        self.storage_attr_name = storage_attr_name
        self.node_factory = node_factory
        
        node_classinfo = listify(node_classinfo)+[NodeABC]
        if inspect.isclass(self.node_factory):
            node_classinfo.append(self.node_factory)
        node_classinfo = tuple(node_classinfo)
            
        self.node_classinfo = node_classinfo
        
    def __get__(self, instance, owner):
        if instance is not None:
            return instance.__dict__[self.storage_attr_name]
        # If the descriptor is called as a class attribute, it
        # just returns itself, to allow the world to see that it 
        # is a descriptor
        else:
            return self
    
    def __set__(self, instance, value):
        if not isinstance(value, self.node_classinfo):
            value = self.node_factory(value)
        instance.__dict__[self.storage_attr_name] = value
        
class NodeBase(NodeABC):
    """This class is the base classes of most nodes.
    
    It provides some default implementations for methods of :class:`NodeABC`.
    """
    @classmethod
    def ensure_node(cls, obj, factory=None):
        """Ensure that the given object *obj* is an instance of the class this method is called from or of :class:`NodeABC`
        , and if not, tries to build a node from it using the class this class method is called from or *factory*.

        .. note:: You should better use the :class:`EnsureNode` descriptor when possible, instead of making a use of
                  this class method.
                  
        .. warning:: Not every class supports to be called whith only one parameter, so a call to this
                     class method is note is not guaranteed to succeed.
        
        
        :param obj: the object to build a node from.
        :param factory: an optional factory used to build the node from *obj*. If not provided, the class this 
                        method is called from is called whith *obj* as first and only parameter.
        """
        
        if isinstance(obj, (cls, NodeABC)):
            return obj
        else:
            if factory is not None:
                return factory(obj)
            else:
                return cls(obj)

    def __init__(self, comment=None, side_comment=None, parent=None):
        """ All of the paramaters should be used as keyword arguments, because they are forwarded from 
            the children classes and the order at the arrival is not guaranteed. 

        :param comment: a comment node that will be printed next to the current node when the source code of
                        the node is generated. Usually, it is a block comment printed before the node
                        in languages that supports them. This comment is printed by the containers such as
                        :class:`NodeContainerBase`, so it does not require any support from the class.
                        
        :param side_comment: a comment that will be printed just by the current node when the source code of
                                the node is generated. Usually, it is a one line comment, printed right to the
                                node. Be aware that this parameter is used by the class in whatever way it wants to,
                                and there is no guarantee it will be printed at all. 
        """
        
        # Should be EnsureNode descriptors with factory using phantom_node when given None in derived classes
        self.comment = comment
        # Should be EnsureNode descriptors with factory using phantom_node when given None in derived classes
        self.side_comment = side_comment
            
        if parent is not None:
            if hasattr(parent, 'adopt_node'):
                parent.adopt_node(self)
            else:
                raise NotImplementedError("The given parent does not support child adoption")
        

    def freestanding_str(self, idt=None):
        """See :class:`NodeABC` for the role of this function.
        
        This implementation just calls *inline_str* and prepends a new line and indentation string.
        """
        idt = Indentation.make_idt(idt)
        snippet = self.inline_str(idt)
        # Do not output anything if the string is empty
        if snippet:
            return '\n'+str(idt)+snippet
        else:
            return ''
    
    def __str__(self, idt=None):
        """This implementation tries to print the node by probing the object for some methods:
        
        1. *decl()*: it is usually used to return a :class:`NodeViewBase` corresponding to the declaration of the node
        2. *defi()*: it is usually used to return a :class:`NodeViewBase` corresponding to the definition of the node
        3. *freestanding_str()*: see :class:`NodeABC`
        """
        # We dont use try: ... except: to avoid catching exceptions
        # occuring inside freestanding_str call
        
        # Try to display a declaration
        if hasattr(self, 'decl'):
            self_decl = self.decl()
            if isinstance(self_decl, NodeABC):
                return self_decl.freestanding_str(idt)
        # Or a definition
        elif hasattr(self, 'defi'):
            self_defi = self.defi()
            if isinstance(self_defi, NodeABC):
                return self_defi.freestanding_str(idt)
        
        else:    
            return self.freestanding_str(idt)
        
    def adopt_node(self, child):
        self.append(child)


class DelegateAttribute:
    """This class is a descriptor that allows an object to use the value of that attribute of another instance.
    
    For example, the comment attribute of a parent node of a :class:`NodeViewBase` instance is used as the comment
    attribute of the :class:`NodeViewBase` instance if the comment attribute was not explicitly set on the 
    :class:`NodeViewBase` instance. When that attribute is set, it uses its own object instead of refering to its parent
    one.
    """
    def __init__(self, attr_name, delegated_to_attr_name, descriptor=None, default_value_list=tuple()):
        """
        :param attr_name: the name of the attribute to manage.
        :param delegated_to_attr_name: the name of the attribute holding a reference to the other instance also 
                                       holding an *attr_name* attribute.
        :param descriptor: a descriptor class, in case the attribute should be managed through a descriptor.
                           This allows basic descriptor chaining.
        :param default_value_list: a list of default values that does not trigger the switch to the local attribute.
                                   For example, if a class set by default a *comment* attribute to None, the attribute
                                   look up should still be made in the other instance. That way, it allows some placeholder
                                   value to be set, without altering the intended behavior.
        """
        self.attr_name = attr_name
        self.delegated_to_attr_name = delegated_to_attr_name
        self.descriptor = descriptor
        self.default_value_list = default_value_list
        
    def __get__(self, instance, owner):
        if instance is not None:
            # If the attribute has been set on the instance, just get it
            if instance.__dict__.get('__'+self.attr_name+'_is_set', False):
                if self.descriptor is not None:
                    return self.descriptor.__get__(instance, owner)
                else:
                    return instance.__dict__[self.attr_name]
                
            # Else it means that the attribute has not been set,
            # so we delegate to the parent
            else:
                parent = getattr(instance, self.delegated_to_attr_name)
                return getattr(parent, self.attr_name)

        # If the descriptor is called as a class attribute, it
        # just returns itself, to allow the world to see that it 
        # is a descriptor
        else:
            return self
    
    def __set__(self, instance, value):
        if self.descriptor is not None:
            self.descriptor.__set__(instance, value)
        else:
            instance.__dict__[self.attr_name] = value
        
        # If the value is one of the default_value_list, do not consider that the attribute was
        # set. This allows some code in base classes to set the attribute to None
        # by default, and still get the parent's attribute when it is the case
        if value not in self.default_value_list:
            instance.__dict__['__'+self.attr_name+'_is_set'] = True
            

class NodeViewBase(NodeBase):
    """This is the base class of the node that are view of other node.
    
    For example, a variable declaration is a view of the variable, as it only displays
    informations already contained in the variable object.
    View nodes should store the reference of their parent in a *parent* attribute.
    """
    def __init__(self, parent, *args, **kwargs):
        self.parent = parent
        super().__init__(*args, **kwargs)
    
    def __eq__(self, other):
        """implementation of the equality test between two views:
        it tests to see if they have the same parent and if the two view 
        are of the exact same type.
        """
        return type(self) is type(other) and self.parent is other.parent
    


class PhantomNode(NodeBase):
    """This class is a node that will be printed as an empty string.
    
    This is intended to be used as a placeholder whan a :class:`NodeABC` instance is required.
    """
    # PhantomNode must not call Node.__init__ because it causes infinite
    # recursion when built from Node.__init__
    def __init__(self, *args, **kwargs):
        self.parent = self
        self.comment = self
        self.side_comment = self
    
    def inline_str(self, idt=None):
        return ''
    
    freestanding_str = inline_str

# Instance used everywhere, instead of creating billions of identical PhantomNode
PHANTOM_NODE = PhantomNode()


class NodeContainerBase(NodeBase, collections.MutableSequence, NonIterable):
    """This is the base class of all the nodes that contains a list of other nodes.
    
    It implements all the logic for operators overloading, and printing the nodes that it take care of.
    It also derives from the :class:`collections.MutableSequence` abstract base class, so it behaves
    like a list. The only exception is when given to :func:`listify`, it remains as a single object, because
    it also derives from :class:`NonIterable`. This is intended to allow the user to add nodes to it later,
    and the result should be taken into account by the consumer that used :func:`listify` on it. If it was not the case,
    the consumer using :func:`listify` would end up with a list of nodes frozen at the time :func:`listify` is called.
    
    The other important aspect of this class is that it can guarantee the type of the contained nodes, even when
    overloaded operators like *+=* are used. See the *node_classinfo* and *node_factory* constructor arguments.
    """
    
    default_node_classinfo = (NodeABC,)
    
    def __init__(self, node_list=None, node_classinfo=None, node_factory=None, *args, **kwargs):
        """
        :param node_list: the list of nodes that the container contains
        :param node_classinfo: a tuple of classes used to check the nodes that enters the container.
                               If a node is not an instance of one of the *node_classinfo* classes, it is
                               passed to *node_factory*. All of the classes in *node_classinfo* must be 
                               subclasses of :class:`NodeABC`.
        :param node_factory: a factory used when an object which is not an instance of one of the classes of 
                             *node_classinfo* tries to enter the container. The return value of this factory 
                             is then allowed inside.
        """
        node_classinfo_tuple = tuple(listify(node_classinfo))
        for classinfo in node_classinfo_tuple:
            if not issubclass(classinfo, NodeABC):
                raise ValueError('node_classinfo must be a subclass of NodeABC')
            
        node_list = listify(node_list)
        
        if node_classinfo is None:
            self.node_classinfo = self.default_node_classinfo
        else:
            self.node_classinfo = node_classinfo_tuple
            
        if node_factory is None:
            # If the node_classinfo is None, then self.node_classinfo contains default_node_classinfo
            # which is only composed of NodeABC, and therefore cannot be used as a factory
            if node_classinfo is None:
                raise ValueError(
                    'You must specify a node factory or give a class that can be used as a factory as first item of node_classinfo'
                )
            
            # The first element in the tuple is taken as the factory
            node_factory = self.node_classinfo[0]
        
        # A wrapper to make sure that the output of the node_factory is 
        # indeed a NodeABC
        def make_node_factory_wrapper(factory):
            def wrapper(node):
                result = factory(node)
                if not isinstance(result, NodeABC):
                    raise ValueError("The node factory did not give a NodeABC")
                else:
                    return result
            return wrapper
                
        self.node_factory = make_node_factory_wrapper(node_factory)
        
        self.node_list = [
            item if isinstance(item, self.node_classinfo) else self.node_factory(item)
            for item in node_list
        ]
        super().__init__(*args, **kwargs)
    
    def inline_str(self, idt=None):
        """Print all the contained nodes using their *freestanding_str* method,
        because a container is a freestanding context.
        It also strips the blank lines at the beginning.
        """
        snippet = ""
        for node in self.node_list:
            if hasattr(node, 'comment'):
                snippet += node.comment.freestanding_str(idt)
            snippet += node.freestanding_str(idt)
         
        return strip_starting_blank_lines(snippet)
    
    def freestanding_str(self, idt=None):
        """Calls super().freestanding_str, and strip the blank lines
        at the beginning.
        """
        snippet = super().freestanding_str(idt)
        return strip_starting_blank_lines(snippet)
    
    def __copy__(self):
        cls = type(self)
        new_obj = cls.__new__(cls)
        new_obj.__dict__.update(self.__dict__)
        new_obj.node_list = copy.copy(self.node_list)
        new_obj.node_classinfo = copy.copy(self.node_classinfo)
        new_obj.node_factory = copy.copy(self.node_factory)
        return new_obj
    
    def clear(self):
        # We preserve the object's itself, we do not build a new one
        self[:] = []

    def insert(self, index, value):
        elem_list = listify(value)
        for i, elem in enumerate(elem_list):
            if not isinstance(elem, self.node_classinfo):
                elem = self.node_factory(elem)
            self.node_list.insert(index+i, elem)


    def index(self, *args, **kwargs):
        return self.node_list.index(*args, **kwargs)
        
    def count(self, *args, **kwargs):
        return self.node_list.count(*args, **kwargs)
                
    def pop(self, *args, **kwargs):
        return self.node_list.pop(*args, **kwargs)
        
    def reverse(self):
        self.node_list.reverse()
        
    def remove(self, *args, **kwargs):
        self.node_list.remove(*args, **kwargs)
    
    @abc.abstractmethod
    def __add__(self, other):
        return type(self)((self, other))
    
    @abc.abstractmethod
    def __radd__(self, other):
        return type(self)((other, self))

    def __iadd__(self, other):
        other_list = listify(other)
        typed_other_list = [
            item if isinstance(item, self.node_classinfo) else self.node_factory(item)
            for item in other_list
        ]
        self.node_list.extend(typed_other_list)
        return self
        
    def append(self, other):
        self.__iadd__(other)
        
    def extend(self, other_list):
        other_list = listify(other_list)
        for other in other_list:
            self.append(other)                

    def __mul__(self, other):
        if isinstance(other, numbers.Integral):
            self_copy = copy.copy(self)
            self_copy.node_list = self.node_list * other
            return self_copy            
        else:
            return NotImplemented

    def __rmul__(self, other):
        return self.__mul__(other)

    def __imul__(self, other):
        if isinstance(other, numbers.Integral):
            self.node_list *= other
            return self
        else:
            return NotImplemented

    def __contains__(self, item):
        return item in self.node_list
        
    def __reversed__(self):
        return reversed(self.node_list)
        
    def __getitem__(self, key):
        return self.node_list[key]
        
    def __setitem__(self, key, value):
        if not isinstance(value, self.node_classinfo):
            value = self.node_factory(value)
        
        self.node_list[key] = value        
                            
    def __delitem__(self, key):
        del self.node_list[key]
        
    def __len__(self):
        return len(self.node_list)
        
    def __iter__(self):
        return iter(self.node_list)


class TokenListABC(NodeBase, NonIterable, collections.MutableSequence):
    """This class is an abstract base class for all classes that are token lists.
    
    A token list is an object that holds a sequence of tokens, which get concatenated when printed.
    The tokens are turned into strings only when the token list is printed, which is why it is 
    the lazy building blocks of source code constructs like expressions and many others.
    
    Whan printed, the token list should call *inline_str* on its tokens if the token is a :class:`NodeABC`,
    or the builtin :func:`str` otherwise.
    """
    pass

class DelegatedTokenListBase(TokenListABC):
    """This is the base class for token lists classes that forward the calls to the :class:`TokenListABC` API
    to an attribute.
    
    This class implements stubs to allow transparent object composition.
    """
    @property
    def tokenlist_attr(self):
        """This property gives the attribute holding the real token list."""
        
        attr = getattr(self, self.tokenlist_attr_name)
        if not isinstance(attr, TokenListABC):
            raise AttributeError('The attribute '+self.tokenlist_attr_name+' is not a TokenListABC')
        else:
            return attr
    
    @tokenlist_attr.setter
    def tokenlist_attr(self, value):
        return setattr(self, self.tokenlist_attr_name, value)
    
    def __init__(self, tokenlist_attr_name, *args, **kwargs):
        """
        :param tokenlist_attr_name: the name of the attribute holding the real token list
        """
        
        self.tokenlist_attr_name = tokenlist_attr_name
        super().__init__(*args, **kwargs)
        
    def inline_str(self, idt=None):
        return self.tokenlist_attr.inline_str(idt)
    
    def freestanding_str(self, idt=None):
        return self.tokenlist_attr.freestanding_str(idt)

    def index(self, *args, **kwargs):
        return self.tokenlist_attr.index(*args, **kwargs)
        
    def insert(self, *args, **kwargs):
        return self.tokenlist_attr.insert(*args, **kwargs)

    def index(self, *args, **kwargs):
        return self.tokenlist_attr.index(*args, **kwargs)
        
    def count(self, *args, **kwargs):
        return self.tokenlist_attr.count(*args, **kwargs)
                
    def pop(self, *args, **kwargs):
        return self.tokenlist_attr.pop(*args, **kwargs)
        
    def reverse(self):
        self.tokenlist_attr.reverse()
        
    def remove(self, *args, **kwargs):
        self.tokenlist_attr.remove(*args, **kwargs)

    def __add__(self, other):
        self_copy = copy.copy(self)
        self_copy.tokenlist_attr = self_copy.tokenlist_attr.__add__(other)
        return self_copy
        
    def __radd__(self, other):
        self_copy = copy.copy(self)
        self_copy.tokenlist_attr = self_copy.tokenlist_attr.__radd__(other)
        return self_copy
        
    def append(self, other):
        self.tokenlist_attr.append(other)

    def __iadd__(self, *args, **kwargs):
        self.tokenlist_attr.__iadd__(*args, **kwargs)
        return self

    def extend(self, other_list):
        self.tokenlist_attr.extend(other_list)
        
    def __mul__(self, other):
        self_copy = copy.copy(self)
        self_copy.tokenlist_attr = self_copy.tokenlist_attr.__mul__(other)
        return self_copy
        
    
    def __rmul__(self, *args, **kwargs):
        self_copy = copy.copy(self)
        self_copy.tokenlist_attr = self_copy.tokenlist_attr.__rmul__(*args, **kwargs)
        return self_copy
        

    def __imul__(self, other):
        self.tokenlist_attr.__imul__(other)
        return self
    
    def __contains__(self, *args, **kwargs):
        return self.tokenlist_attr.__contains__(*args, **kwargs)
        
    def __iter__(self):
        return self.tokenlist_attr.__iter__()
        
    def __reversed__(self):
        return self.tokenlist_attr.__reversed__()
        
    def __getitem__(self, key):
        return self.tokenlist_attr.__getitem__(key)

    def __setitem__(self, key, value):
        self.tokenlist_attr.__setitem__(key, value)

    def __delitem__(self, key):
        self.tokenlist_attr.__delitem__(key)

    def __len__(self):
        return self.tokenlist_attr.__len__()


class TokenListBase(TokenListABC):
    """This base class implements the :class:`TokenListABC` API with all of the operators overloading logic.
    """
    def __init__(self, token_list=None, *args, **kwargs):
        """
        :param token_list: the list of tokens to store inside the token list
        """
        self._token_list = listify(token_list)
        super().__init__(*args, **kwargs)

    def inline_str(self, idt=None):
        """Print the tokens of the token list usin, and concatenate all the strings.
        
        If the token is a :class:`NodeABC`, its *inline_str* method is used.
        otherwise, :func:`str` builtin is called on the token.
        """
        string = ''
        for token in self._token_list:
            if token is self:
                # Special handling of self: allows to print itself using
                # a different method to avoid infinite recursion and to provide
                # a mean to subclasses to implement self printing without creating a 
                # "self-printer" class dedicated to printing themselves
                string += self.self_inline_str(idt)
            elif isinstance(token, NodeABC):
                string += token.inline_str(idt)
            else:
                string += str(token)
                    
        return string
    
    def index(self, *args, **kwargs):
        return self._token_list.index(*args, **kwargs)
        
    def insert(self, *args, **kwargs):
        return self._token_list.insert(*args, **kwargs)

    def index(self, *args, **kwargs):
        return self._token_list.index(*args, **kwargs)
        
    def count(self, *args, **kwargs):
        return self._token_list.count(*args, **kwargs)
                
    def pop(self, *args, **kwargs):
        return self._token_list.pop(*args, **kwargs)
        
    def reverse(self):
        self._token_list.reverse()
        
    def remove(self, *args, **kwargs):
        self._token_list.remove(*args, **kwargs)

    def __add__(self, other):
        if isinstance(other, TokenListABC):
            other_list = list(other)
            self_copy = copy.copy(self)
            self_copy._token_list = self._token_list+other_list
            return self_copy
        # The result of the addition with a NodeContainer is a NodeContainer
        elif isinstance(other, NodeContainerBase):
            return other.__radd__(self)
        else:
            other_list = listify(other)
            self_copy = copy.copy(self)
            self_copy._token_list = self._token_list+other_list
            return self_copy

    def __radd__(self, other):
        other_list = listify(other)
        self_copy = copy.copy(self)
        self_copy._token_list = other_list+self._token_list
        return self_copy        

    def append(self, other):
        if isinstance(other, TokenListABC):
            other_list = tuple(other)
        else:
            other_list = listify(other)
            
        self._token_list.extend(other_list)
        return self

    def __iadd__(self, *args, **kwargs):
        self.append(*args, **kwargs)
        return self

    def extend(self, other_list):
        other_list = listify(other_list)
        for other in other_list:
            self.append(other)
        
    def __mul__(self, other):
        if isinstance(other, numbers.Integral):
            self_copy = copy.copy(self)
            self_copy._token_list = self._token_list * other
            return self_copy
        else:
            return NotImplemented

    def __rmul__(self, *args, **kwargs):
        return self.__mul__(*args, **kwargs)

    def __imul__(self, other):
        if isinstance(other, numbers.Integral):
            self._token_list *= other
            return self
        else:
            return NotImplemented

    def __contains__(self, *args, **kwargs):
        return self._token_list.__contains__(*args, **kwargs)
        
    def __iter__(self):
        return iter(self._token_list)
        
    def __reversed__(self):
        return reversed(self._token_list)
        
    def __getitem__(self, key):
        return self._token_list[key]

    def __setitem__(self, key, value):
        self._token_list[key] = value

    def __delitem__(self, key):
        del self._token_list[key]

    def __len__(self):
        return len(self._token_list)


class _IndentedTokenListBase:
    """This class is the base class that implements a token list which indents its content when printed."""
    def inline_str(self, idt=None):
        idt = Indentation.make_idt(idt)
        
        snippet = super().inline_str(idt)
        indented_new_line = "\n"+str(idt)
        snippet = snippet.replace("\n", indented_new_line)
        return snippet

class IndentedTokenListBase(_IndentedTokenListBase, TokenListBase):
    """This class is a base class for token lists that indent their content when printed."""
    pass

class IndentedDelegatedTokenListBase(_IndentedTokenListBase, DelegatedTokenListBase):
    """This is a mix between :class:`DelegatedTokenListBase` and :class:`IndentedTokenListBase`."""
    pass

class BacktraceBase(TokenListBase, NonIterable, metaclass=abc.ABCMeta):
    """This base class allows the instances to record the backtrace of the Python code that 
    created them.
    
    This allows one to add comments in generated source code showing which file and line of the Python
    script was responsible for creating it. This is a facility when debugging the source code generator, 
    and can avoid headache when ones want to track down which line of Python generated which line of
    generated source code.
    As a convenience, it is a subclass of :class:`TokenListBase` so it can be used inside a comment for example.
    """
    __frame_format_string = '{filename}:{lineno}({function})'
    __frame_joiner = ', '
    
    def __init__(self, level=0, *args, **kwargs):
        stack = inspect.stack()
        self.stack_frame_list = [
            frame[1:] for frame in stack
            if os.path.dirname(frame[1]) != os.path.dirname(__file__)
        ]

        super().__init__(self, *args, **kwargs)
    
    @abc.abstractmethod
    def freestanding_str(self, idt=None):
        #Construct a comment by giving it self as a token and use its freestanding_str method
        pass

    def self_inline_str(self, idt=None):
        return self.__frame_joiner.join(
            self.__frame_format_string.format(
                filename = os.path.relpath(frame[0]),
                lineno = frame[1],
                function = frame[2],
                line_content = frame[3][frame[4]] if frame[3] is not None else ''
            ) for frame in self.stack_frame_list
        )