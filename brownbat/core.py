

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
    

import collections
import numbers
import abc
import inspect
import copy 

def listify(iterable_or_single_elem):
    if iterable_or_single_elem is None:
        return []
    # We exclude iterables such as strings or NonSequence (StmtContainer for example)
    # because we want to keep them as one object and not split them
    if isinstance(iterable_or_single_elem, collections.Iterable) \
        and not isinstance(iterable_or_single_elem, (str, NonSequence)):
        return list(iterable_or_single_elem)
    else:
        return [iterable_or_single_elem]

def format_string(string, style, separator="_"):
    """ Format identifiers
    The input string is assumed to be like this: lower_case_with_underscore
    """
    if isinstance(string, collections.Iterable) and not isinstance(string, (str, NonSequence)):
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
    last_new_line_pos = 0
    for position, char in enumerate(snippet):
        if char=='\n':
            last_new_line_pos = position
        elif char!='\t' and char!=' ' and char!='\v':
            break
    # Only keep one new line at the beginning, to avoid multiple blank lines
    return snippet[last_new_line_pos:]

class Indentation:
    # Default indentation style (4 spaces)
    indentation_string = '    '
    
    @classmethod
    def make_idt(cls, idt):
        if idt is None:
            idt = cls()
        elif isinstance(idt, numbers.Integral):
            idt = cls(idt)
        elif isinstance(idt, str):
            idt = cls(indentator=idt) 
        return idt
        
    
    def __init__(self, level=0, indentator=None):
        self.indentation_level = level
        # If an indentation is string is given, override the classwide default with
        # an instance-local string
        if indentator is not None:
            self.indentation_string = indentator

    def indent(self, level=1):
        self.indentation_level += level

    def dedent(self, level=1):
        self.indentation_level -= level

    def __str__(self):
        return self.indentation_string * self.indentation_level
    

class NonSequence:
    """ Inheriting from this class will prevent a class to be considered as
        collections.Iterable by listify and the like
    """
    pass

class NodeMeta(abc.ABCMeta):
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
    __format_string = ''
    
    @abc.abstractmethod
    def inline_str(self, idt=None):
        pass
    @abc.abstractmethod
    def freestanding_str(self, idt=None):
        pass
    
    @abc.abstractmethod
    def adopt_node(self, child):
        pass

class NodeAttrProxy(NodeABC):
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
    def __init__(self, storage_attr_name, node_factory, node_classinfo=()):
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

    @classmethod
    def ensure_node(cls, obj, factory=None):
        if isinstance(obj, (cls, NodeABC)):
            return obj
        else:
            if factory is not None:
                return factory(obj)
            else:
                return cls(obj)

    def __init__(self, comment=None, side_comment=None, parent=None):
        # Should be EnsureNode descriptors with factory using phantom_node when given None in derived classes
        self.comment = comment
        # Should be EnsureNode descriptors with factory using phantom_node when given None in derived classes
        self.side_comment = side_comment
            
        if parent is not None:
            if hasattr(parent, 'adopt_node'):
                parent.adopt_node(self)
            else:
                raise NotImplementedError("The given parent does not support child adoption")
        
    def __repr__(self):
        return(str(type(self))+str(self.__dict__))

    def freestanding_str(self, idt=None):
        idt = Indentation.make_idt(idt)
        snippet = self.inline_str(idt)
        # Do not output anything if the string is empty
        if snippet:
            return '\n'+str(idt)+snippet
        else:
            return ''
    
    def __str__(self, idt=None):
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
    def __init__(self, attr_name, delegated_to_attr_name, descriptor=None, default_value_list=tuple()):
        self.attr_name = attr_name
        self.delegated_to_attr_name = delegated_to_attr_name
        self.descriptor = descriptor
        self.default_value_list = default_value_list
        
    def __get__(self, instance, owner):
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
    
    def __set__(self, instance, value):
        if self.descriptor is not None:
            self.descriptor.__set__(instance, value)
        else:
            instance.__dict__[self.attr_name] = value
        
        # If the value is None, do not consider that the attribute was
        # set. This allows some code in base classes to set the attribute to None
        # by default, and still get the parent's attribute when it is the case
        if value not in self.default_value_list:
            instance.__dict__['__'+self.attr_name+'_is_set'] = True
            

class NodeViewBase(NodeBase):
    def __eq__(self, other):
        return self.parent is other.parent
    


class PhantomNode(NodeBase):
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
phantom_node = PhantomNode()


class NodeContainerBase(NodeBase, collections.MutableSequence, NonSequence):
    default_node_classinfo = (NodeABC,)
    
    def __init__(self, node_list=None, node_classinfo=None, node_factory=None, *args, **kwargs):
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
            self.node_factory = self.node_classinfo[0]
        else:
            self.node_factory = node_factory
        
        self.node_list = [
            item if isinstance(item, self.node_classinfo) else self.node_factory(item)
            for item in node_list
        ]
        super().__init__(*args, **kwargs)
    
    def inline_str(self, idt=None):
        snippet = ""
        for node in self.node_list:
            if hasattr(node, 'comment'):
                snippet += node.comment.freestanding_str(idt)
            snippet += node.freestanding_str(idt)
         
        return strip_starting_blank_lines(snippet)
    
    def freestanding_str(self, idt=None):
        snippet = super().freestanding_str(idt)
        return strip_starting_blank_lines(snippet)
    
    def copy(self):
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


class TokenListABC(NodeBase, NonSequence, collections.MutableSequence):
    pass

class DelegatedTokenListBase(TokenListABC):
    @property
    def tokenlist_attr(self):
        attr = getattr(self, self.tokenlist_attr_name)
        if not isinstance(attr, TokenListABC):
            raise AttributeError('The attribute '+self.tokenlist_attr_name+' is not a TokenListABC')
        else:
            return attr
    
    @tokenlist_attr.setter
    def tokenlist_attr(self, value):
        return setattr(self, self.tokenlist_attr_name, value)
    
    def __init__(self, tokenlist_attr_name, *args, **kwargs):
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
    def __init__(self, token_list=None, *args, **kwargs):
        self._token_list = listify(token_list)
        super().__init__(*args, **kwargs)

    def inline_str(self, idt=None):
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
    def inline_str(self, idt=None):
        idt = Indentation.make_idt(idt)
        
        snippet = super().inline_str(idt)
        indented_new_line = "\n"+str(idt)
        snippet = snippet.replace("\n", indented_new_line)
        return snippet

class IndentedTokenListBase(_IndentedTokenListBase, TokenListBase):
    pass

class IndentedDelegatedTokenListBase(_IndentedTokenListBase, DelegatedTokenListBase):
    pass

