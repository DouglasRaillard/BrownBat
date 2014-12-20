
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

C langage source code generation module

This module provides C langage specific classes.
"""

    
import collections
import numbers
import textwrap
import re
import builtins
import inspect
import os
import copy

import brownbat.core as core

class Configuration:
    """This class holds configuration keys used to modify the behavior of the module.
    """
    def __init__(self, enable_debug_comments):
        """
        :param enable_debug_comments: enables automatic debugging comments in generated sources. Automatic comments are built with the line of the Python code that created the object represented and its type.
            
        """
        self.enable_debug_comments = enable_debug_comments

default_config = Configuration(
    enable_debug_comments = False
)

class Node(core.NodeBase):
    """This class is at the root of the inheritance hierarchy of this module.
    
    It handles some features which are common to all of the classes representing C source code.
    """
    
    config = default_config
    
    # We must check if the comment is None to avoid infinite recursion
    # because Com tries to build a TokenList (via TokenListContainer) with comment=None, which in turn
    # tries to build a comment with None and so on
    comment = core.EnsureNode('comment', lambda x: Com(x) if x is not None else core.PHANTOM_NODE)
        
    # We must check if the comment is None to avoid infinite recursion
    # because SingleLineCom tries to build a TokenList with comment=None, which in turn
    # tries to build a comment with None and so on
    side_comment = core.EnsureNode('side_comment', lambda x: SingleLineCom(x) if x is not None else core.PHANTOM_NODE)
        
    def __init__(self, comment=None, side_comment=None, parent=None, config=None):
        """
        :param comment: is the multiline comment node associated to this node. If it is not already a :class:`~brownbat.core.NodeABC`,
                        a :class:`.Com` will be built with what you give to it.
        :param side_comment: is a single line comment associated with this node. It will be an instance of :class:`.SingleLineCom`
                             if it is not already a :class:`~brownbat.core.NodeABC`.
                             Be aware that this side comment must be displayed by the class, and sometimes it will not be printed.
        :param parent: is the parent of the node if this is a :class:`NodeView`.
        :param config: is the configuration object of this instance. It defaults to using the *config* class attribute,
                       so changing the class attribute *config* will impact all the instances that has not overriden
                       it by providing a configuration object explicitly.
        """
        
        if config is not None:
            self.config = config
        
        # /!\ Be carefull here: as this class is the base class of all classes
        # in this file, any constructor call here will turn into infinite
        # recursion. Fortunately, side_comment is irrelevant for Backtrace
        if self.config.enable_debug_comments and not isinstance(self, (Backtrace, SingleLineCom)):
            side_comment = SingleLineCom((self.__class__.__name__+' created at '+Backtrace()))
            
        super().__init__(comment=comment, side_comment=side_comment, parent=parent)

class NodeView(core.NodeViewBase, Node):
    """This class is the C implementation of :class:`~brownbat.core.NodeViewBase` class.
    """
    side_comment = core.DelegateAttribute(
        'side_comment', 'parent',
        descriptor = Node.side_comment,
        default_value_list = (None,)
    )
    """Side comment which defaults to using the *parent.side_comment* attribute
    when not set explicitly.
    """
    
    comment = core.DelegateAttribute(
        'comment', 'parent',
        descriptor = Node.comment,
        default_value_list = (None,)
    )
    """Comment which defaults to using the *parent.comment* attribute
    when not set explicitly.
    """

class NodeContainer(core.NodeContainerBase, Node):
    """This is the C implementation of :class:`~brownbat.core.NodeContainerBase` class.
    
    It overrides *__add__* and *__radd__* to return a :class:`.TokenListContainer` instance that
    combines both operands.
    """
    
    def __add__(self, other):
        # TokenListContainer are the most agnostic containers
        return TokenListContainer((self, other))
    
    def __radd__(self, other):
        # TokenListContainer are the most agnostic containers
        return TokenListContainer((other, self))
    

class TokenListContainer(NodeContainer):
    """This class is a :class:`NodeContainer` subclass that uses :class:`TokenList` as 
    factory when the nodes given to it are not instances of subclasses of :class:`~brownbat.core.NodeABC`.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(node_classinfo=TokenList, *args, **kwargs)

class TokenList(core.TokenListBase, Node):
    """This class is the C implementation of :class:`~brownbat.core.TokenListBase`."""
    pass

class DelegatedTokenList(core.DelegatedTokenListBase, Node):
    """This class is the C implementation of :class:`~brownbat.core.DelegatedTokenListBase`."""
    pass

class IndentedTokenList(core.IndentedTokenListBase, TokenList):
    """This class is the C implementation of :class:`~brownbat.core.IndentedTokenListBase`."""
    pass

class IndentedDelegatedTokenList(core.IndentedDelegatedTokenListBase, DelegatedTokenList):
    """This class is the C implementation of :class:`~brownbat.core.IndentedDelegatedTokenListBase`."""
    pass

class Backtrace(core.BacktraceBase, TokenList):
    """This class is the C implementation of :class:`~brownbat.core.BacktraceBase`.
    
    It is printed as :class:`.SingleLineCom` when using *freestanding_str*.
    """    
    def freestanding_str(self, idt=None):
        return SingleLineCom(('Object built at ', self)).freestanding_str(idt)


class _Expr:
    __format_string = '{expr};{side_comment}'
    
    def freestanding_str(self, idt=None):
        idt = core.Indentation.make_idt(idt)
        side_comment = self.side_comment
        snippet = '\n'+str(idt)+self.__format_string.format(
            expr = self.inline_str(idt),
            side_comment = side_comment.inline_str(idt)
        )
        return snippet


    def assign(self, value):
        return Expr((self," = ",value))
    
    def cast(self, new_type):
        return Expr(('((',new_type,')(',self,'))'))

    def rcast(self, casted):
        return Expr(('((',self,')(',casted,'))'))
        
    def deref(self):
        return Expr(('(*(',self,'))'))
            
    def paren(self):
        return Expr(('(',self,')'))
    
    def address(self):
        return Expr(('(&(',self,'))'))
        
    def __rshift__(self, member):
        """Right shift allows to access structure/union/enum members: 'a'>>'b' will give 'a.b'."""
        return Expr((self,".",member))
    
    def __rrshift__(self, basename):
        """See right shift"""
        return Expr((basename,".",self))

    def __invert__(self):
        """ ~expr will give (&(expr))"""
        return self.address()
       
    def __pos__(self):
        """ +expr will give (*(expr))"""
        return self.deref()
    
    def __neg__(self):
        """-expr will give (expr)"""
        return self.paren()

    def __pow__(self, type):
        """expr1**expr2 will give ((expr1)(expr2))"""
        return self.rcast(type)
    
    def __rpow__(self, type):
        """'int'**expr will give ((int)(expr))"""
        return self.cast(type)
    
class Expr(_Expr, IndentedTokenList):
    """This class represents a C expression.
    
    It is a subclass of :class:`.IndentedTokenList`, and extends its *freestanding_str* method by
    printing a *;* at the end of line.
    """
    pass

class DelegatedExpr(_Expr, IndentedDelegatedTokenList):
    """This class represent a C expression.
    
    This variant of :class:`.Expr` uses an attribute to hold the real :class:`.Expr`. It allows
    to transparently use composition to store the expression.
    """
    pass
    

class StmtContainer(NodeContainer, core.NonIterable):
    """This class is a :class:`.NodeContainer` that uses :class:`Expr` as its factory.
    
    It allows the user to append plain strings for example, and expressions will be automatically built out of them.
    """
    def __init__(self, node_list=None, node_classinfo=None, node_factory=None, *args, **kwargs):
        node_classinfo_list = core.listify(node_classinfo)
        if node_classinfo is None:
            node_classinfo_list = [core.NodeABC]
            
        # Only force node_factory if node_classinfo is empty, because a empty
        # node_factory will be filled with the first element of node_classinfo by NodeContainer
        if node_factory is None and node_classinfo is None:
            node_factory = Expr
        
        super().__init__(node_list=node_list, node_classinfo=node_classinfo_list, node_factory=node_factory, *args, **kwargs)
        
    
class BlockStmt(StmtContainer):
    """This class is a subclass of :class:`.StmtContainer`.
    
    It extends *inline_str* by outputing *{* at the front and *}* at the end, 
    and also indent its content.
    """
    def inline_str(self, idt=None):
        idt = core.Indentation.make_idt(idt)
        # Hide side comment for derived class because
        # they usually display it in their own format
        if self.__class__ is BlockStmt:
            side_comment = self.side_comment.inline_str(idt)
        else:
            side_comment = ''
        
        snippet = '\n'+str(idt)+'{'+side_comment
        idt.indent()
        snippet += super().inline_str(idt)
        idt.dedent()
        snippet += '\n'+str(idt)+'}'
        
        return snippet


class OrderedTypeContainer(StmtContainer):
    """This class is a container that automatically reorder
    compound type definitions to satisfy the dependencies.
    
    It inserts the reordered type definitions at the beginning,
    and also include a forward declaration for each type, to allow
    pointer cross-referencing.
    """
    
    def inline_str(self, idt=None):
        # Only touch the a copy
        self_copy = copy.copy(self)
        
        # Build a dictionary mapping the type names to the type objects
        type_dict = collections.OrderedDict()
        for item in self:
            if isinstance(item, (Struct, Union)):
                type_dict[item.name.inline_str().strip()] = item
        
        types_to_sort_list = list()
        # Build a dependency graph of unions and structures
        dependency_dict = collections.defaultdict(list)
        # Build a dependency graph of unions and structures that takes pointers into account
        weak_dependency_dict = collections.defaultdict(list)
        # Translation table used to remove character from type name to analyse weak dependencies
        transtable = str.maketrans({char:None for char in '*()'})
        for item in type_dict.values():
            for member in item:
                # Determine dependencies with the type name, to
                # allow hardcoded types to be taken into account
                member_type_name = member.type.inline_str().strip()
                # Remove the leading part to correctly match the real type name
                # WARNING: if a 'struct foo' and 'enum foo' are both declared, it will break and
                # register incorrect depencencies, but it would be insane to do such a thing anyway.
                for prefix in ('struct', 'enum', 'union'):
                    if member_type_name.startswith(prefix):
                        member_type_name = member_type_name[len(prefix):].lstrip()
                        break
                
                # Try to find a type with the exact name
                try:
                    type_ = type_dict[member_type_name]
                    # Only try to access [item] key after making sure the type exists,
                    # to avoid triggering the creation of an empty list, and having 
                    # a key in dependency_dict with no dependencies
                    dependency_dict[item].append(type_)
                    
                    # Build a list of types that will be reordered
                    types_to_sort_list.append(item)
                # If the type name is not found, try to add it as a weak dependency
                except KeyError:
                    # Try to find something that looks like a pointer to a known type
                    stripped_member_type_name = member_type_name.translate(transtable).strip()
                    try:
                        # Only try to access [item] key after making sure the type exists,
                        # to avoid triggering the creation of an empty list, and having 
                        # a key in weak_dependency_dict with no dependencies
                        type_ = type_dict[stripped_member_type_name]
                        weak_dependency_dict[item].append(type_)
                       
                       # Build a list of types that will be reordered
                        types_to_sort_list.append(item)               
                    # If nothing was found, give up
                    except KeyError:
                        pass
        
        # Do a topological sort of the dependency graph of the types
        sorted_node_list = list()
        temporary_marked = set()
        permanently_marked = set()
        
        forward_decl_type_set = set()
        def visit(node):
            nonlocal temporary_marked
            nonlocal permanently_marked
            nonlocal sorted_node_list
            if node in temporary_marked:
                raise ValueError('The dependency graph of compound types is not a DAG, cannot sort the type definitions')
            elif node not in permanently_marked:
                temporary_marked.add(node)
                for dep_node in dependency_dict[node]:
                    visit(dep_node)
                for dep_node in weak_dependency_dict[node]:
                    try:
                        # Backup all data structures in case the DFS fails
                        sorted_node_list_backup = copy.copy(sorted_node_list)
                        temporary_marked_backup = copy.copy(temporary_marked)
                        permanently_marked_backup = copy.copy(permanently_marked)
                        forward_decl_type_set_backup = copy.copy(forward_decl_type_set)
                        
                        visit(dep_node)

                    except ValueError:
                        forward_decl_type_set.add(dep_node)
                        # Restore bookkeeping data
                        sorted_node_list = sorted_node_list_backup
                        temporary_marked = temporary_marked_backup
                        permanently_marked = permanently_marked_backup
                        

                permanently_marked.add(node)
                temporary_marked.discard(node)
                sorted_node_list.append(node)
 
        
        # Only consider types that have dependencies
        # types_to_sort_list may have duplicates
        for node in types_to_sort_list:
            visit(node)
        

        # Build a list of nodes that do not contain the reordered type definitions
        # We must be carefull, as the 'not in' operator for lists tests for equality
        sorted_node_id_list = [id(node) for node in sorted_node_list]
        remaining_node_list = [item for item in self if id(item) not in sorted_node_id_list]
        
        # Build a list of forward declaration to add before type definitions
        forward_decl_list = [item.forward_decl() for item in forward_decl_type_set]

        # Insert the reordered type definitions at the beginning
        self_copy[:] = forward_decl_list+sorted_node_list+[NewLine()]+remaining_node_list
        
        # Print using the StmtContainer.inline_str() method
        return super(OrderedTypeContainer, self_copy).inline_str(idt)
    
class ConditionnalStmtBase(BlockStmt):
    cond = core.EnsureNode('cond', TokenList)
    """The condition of the conditional statement."""
    
    def __init__(self, cond=None, *args, **kwargs):
        """
        :param cond: the condition of the conditional statement.
        """
        self.cond = cond
        super().__init__(*args, **kwargs)

    def inline_str(self, idt=None):
        return self.__format_string.format(
            cond = self.cond.inline_str(idt),
            stmt = super().inline_str(idt),
            side_comment = self.side_comment.inline_str(idt),
            idt_nl = '\n'+str(idt)
        )

class If(ConditionnalStmtBase):
    """This class represents the C *if* statement."""
    
    _ConditionnalStmtBase__format_string = "if({cond}){side_comment}{stmt}"
    
class Else(ConditionnalStmtBase):
    """This class represents the C *else* statement.
    
    :param cond: ignored
    """
    
    _ConditionnalStmtBase__format_string = "else{side_comment}{stmt}"
    
    def __init__(self, *args, **kwargs):
        super().__init__(cond=None, *args, **kwargs)
    
class ElseIf(ConditionnalStmtBase):
    """This class represents the C *else if* statement."""
    
    _ConditionnalStmtBase__format_string = "else if({cond}){side_comment}{stmt}"
    
class While(ConditionnalStmtBase):
    """This class represents the C *while* statement."""

    _ConditionnalStmtBase__format_string = "while({cond}){side_comment}{stmt}"

class For(BlockStmt):
    """This class represents the C *for* statement."""
    
    init = core.EnsureNode('init', TokenList)
    """This is the initalization expression (``a`` in ``for(a;b;c){}``)."""
    
    cond = core.EnsureNode('cond', TokenList)
    """This is the stop condition (``b`` in ``for(a;b;c){}``)."""
    
    action = core.EnsureNode('action', TokenList)
    """This is the expression evaluated each time(``c`` in ``for(a;b;c){}``)."""


    __format_string = "for({init}; {cond}; {action}){side_comment}{stmt}"

    def __init__(self, init=None, cond=None, action=None, *args, **kwargs):
        # If we got a variable, we take its definition because it is a really
        # common use case
        if isinstance(init, Var):
            self.init = init.defi()
        else:    
            self.init = init
            
        self.cond = cond
        self.action = action
        super().__init__(*args, **kwargs)
        
    def inline_str(self, idt=None):
        return self.__format_string.format(
            cond = self.cond.inline_str(idt),
            init = self.init.inline_str(idt),
            action = self.action.inline_str(idt),
            stmt = super().inline_str(idt),
            side_comment = self.side_comment.inline_str(idt),
            idt_nl = '\n'+str(idt)
        )


class DoWhile(BlockStmt):
    """This class represents the C *do while* statement."""
    
    cond = core.EnsureNode('cond', TokenList)
    """This is the stop condition."""

    __format_string = "do{side_comment}{stmt}{idt_nl}while({cond});"
    
    def __init__(self, cond=None, *args, **kwargs):
        self.cond = cond
        super().__init__(*args, **kwargs)

    def inline_str(self, idt=None):
        idt = core.Indentation.make_idt(idt)
        
        return self.__format_string.format(
            stmt = super().inline_str(idt),
            cond = self.cond.inline_str(idt),
            side_comment = self.side_comment.inline_str(idt),
            idt_nl = '\n'+str(idt)
        )

class Switch(Node, core.NonIterable, collections.MutableMapping):
    """This class represents the C *switch* statement.
    
    This class can be used as a dictionary (:class:`collections.MutableMapping`)
    with the keys as the case values, and the values as the code to execute when the
    tested expression matches the key.
    """
    
    expr = core.EnsureNode('expr', TokenList)
    """This is the expression to switch on."""
    
    __format_string = "switch({expr}){side_comment}{idt_nl}{{{stmt}{idt_nl}}}"
    __case_format_string = "{idt_nl}case ({case}):{side_comment}{stmt}{auto_break}\n"
    __default_format_string = "{idt_nl}default:{side_comment}{stmt}{auto_break}\n"

    def __init__(self, expr=None, case_map=None, auto_break=True, *args, **kwargs):
        """
        :param expr: the expression to switch on.
        :type expr: :class:`.TokenList` 
        :param case_map: a mapping with keys used as cases and values as
                         the code to execute (a :class:`.StmtContainer`).
        
        :param auto_break: a boolean indicating if a *break* statement should be 
                           automatically inserted at the end of the code of the 
                           cases.
        
        .. note:: The *case_map* keys are not touched, so you may use them later, they
                  will not be turned into :class:`.TokenList`.
        """
        self.expr = expr
        processed_case_map = collections.OrderedDict()
        if isinstance(case_map, collections.Mapping):
            for key, value in case_map.items():
                processed_case_map[key] = StmtContainer(value)
        elif case_map is None: pass
        else:
            raise ValueError("You have to give a mapping or None for the case_map")

        self.case_map = processed_case_map
        self.auto_break = auto_break
        super().__init__(*args, **kwargs)

    def inline_str(self, idt=None):        
        idt = core.Indentation.make_idt(idt)
        body = ""
        
        idt.indent()
        for case, stmt in self.case_map.items():
            case = TokenList.ensure_node(case)
            case_string = case.inline_str(idt)
            if case_string == "default":
                format_string = self.__default_format_string
            else:
                format_string = self.__case_format_string

            idt.indent()
            stmt_snippet = stmt.inline_str(idt)
            if self.auto_break:
                auto_break = '\n'+str(idt)+"break;"
            else:
                auto_break = ""
            idt.dedent()
            
            body += format_string.format(
                idt_nl = '\n'+str(idt),
                case = case_string,
                side_comment = case.side_comment.inline_str(idt),
                stmt = stmt_snippet,
                auto_break = auto_break
            )
                
        idt.dedent()
        
        snippet = self.__format_string.format(
            idt_nl = '\n'+str(idt),
            expr = self.expr.inline_str(idt),
            side_comment = self.side_comment.inline_str(idt),
            stmt = body
        )
        return snippet

    def __copy__(self):
        cls = type(self)
        new_obj = cls.__new__(cls)
        new_obj.__dict__.update(self.__dict__)
        new_obj.case_map = copy.copy(self.case_map)
        new_obj.expr = copy.copy(self.expr)
        return new_obj

    def __getitem__(self, key):
        return self.case_map[key]
        
    def __setitem__(self, key, value):
        self.case_map[key] = StmtContainer(value)
                
    def __delitem__(self, key):
        del self.case_map[key]
        
    def __len__(self):
        return len(self.case_map)
        
    def __iter__(self):
        return iter(self.case_map)


class Var(DelegatedExpr):
    storage_list = core.EnsureNode('storage_list', TokenListContainer)
    
    type = core.EnsureNode('type',
        node_factory=lambda type: TokenList(type) if type is not None else None,
        node_classinfo=TokenList
    )
    name = core.EnsureNode('name', node_factory=TokenList)

    _array_size = core.EnsureNode('_array_size',
        node_factory=lambda array_size: TokenList(array_size) if array_size is not None else None,
        node_classinfo=TokenList
    )
    initializer = core.EnsureNode('initializer',
        node_factory=lambda initializer: TokenList(initializer) if initializer is not None else None,
        node_classinfo=TokenList
    )
    
    @property
    def array_size(self):
        # If the array size is not specified, try to use the one from the type
        if self._array_size is None and hasattr(self.type, 'array_size'):
            return self.type.array_size
        else:
            return self._array_size
    
    @array_size.setter
    def array_size(self, value):
        self._array_size = value
    
    c_identifier_regex_str = "[a-zA-Z_]+[a-zA-Z0-9_]*"
    var_defi_name_array_initializer_regex_str = "(?:(?P<name>"+c_identifier_regex_str+")\s*)(?:\[\s*(?P<array_size>.*?)\s*\])?(?:\s*=\s*(?P<initializer>.*?)\s*)?"
    var_defi_storage_list_regex_str = "(?P<storage_list>.*?)"
    var_def_type_regex_str = "(?P<type>(?:(?P<_is_a_compound>union|struct|enum)\s*(?(_is_a_compound)(?:(?:\{.*?\})|(?:"+c_identifier_regex_str+"))|"+c_identifier_regex_str+"))?(?(_is_a_compound)|"+c_identifier_regex_str+")(?:\s*\*+)?)"
        
    # Matches a declaration or definition of a C variable with the following groups:
    #   * name of the variable    
    #   * optionally, array_size. None if the declaration is not an array
    #   * optionally, initializer of the variable. None if not specified
    var_no_type_defi_regex_str = "^\s*"+var_defi_name_array_initializer_regex_str+"\s*$"
    var_no_type_defi_regex = re.compile(var_no_type_defi_regex_str)
        
    # Matches a declaration or definition of a C variable with the following groups:
    #   * type of the variable
    #   * name of the variable    
    #   * optionally, array_size. None if the declaration is not an array
    #   * optionally, initializer of the variable. None if not specified
    var_defi_regex_str = "^\s*"+var_def_type_regex_str+"?\s*"+var_defi_name_array_initializer_regex_str+"\s*$"
    var_defi_regex = re.compile(var_defi_regex_str)

    # Matches a declaration or definition of a C variable with the following groups:
    #   * storage_list of the variable
    #   * type of the variable
    #   * name of the variable    
    #   * optionally, array_size. None if the declaration is not an array
    #   * optionally, initializer of the variable. None if not specified
    var_storage_list_defi_regex = re.compile("^\s*"+var_defi_storage_list_regex_str+"\s+"+var_def_type_regex_str+"\s*"+var_defi_name_array_initializer_regex_str+"\s*$")


    def __init__(self, decl=None, storage_list=None, type=None, name=None, initializer=None, array_size=None, *args, **kwargs):
        
        if decl is not None:
            # Parse the declaration
            if isinstance(decl, str):
                # Try to match without a storage list and without a type
                match = self.var_no_type_defi_regex.match(decl)
                if match is None:
                    # If the previous regex failed to match, try the one with type support
                    match = self.var_defi_regex.match(decl)
                if match is None:
                    # If the previous regex failed to match, try the one with type and storage list support
                    match = self.var_storage_list_defi_regex.match(decl)                
                if match is None:
                    raise ValueError("Cannot parse variable declaration/definition")
                
                # Try to get the storage list if there is one
                try:
                    decl_storage_list = match.group('storage_list').split()
                except IndexError:
                    decl_storage_list = None

                # Try to get the type if there is one
                try:
                    decl_type = match.group('type')
                except IndexError:
                    decl_type = None
                    
                # Remove multiple spaces before the star in pointer declarations
                # for example: "    *" => " *"
                if decl_type is not None:
                    try:
                        first_star_index = decl_type.index('*')
                        decl_type = decl_type[:first_star_index].strip()+' '+decl_type[first_star_index:].strip()
                    # No star was found
                    except ValueError:
                        pass
                    
                decl_name = match.group('name')                
                decl_array_size = match.group('array_size')
                decl_initializer = match.group('initializer')
            
            # Make a shallow copy of the other Var
            elif isinstance(decl, Var):
                decl_storage_list = decl.storage_list
                decl_type = decl.type
                decl_name = decl.name
                decl_array_size = decl.array_size
                decl_initializer = decl.initializer
                
            # Use a TokenList as the name of the variable, nothing else
            elif isinstance(decl, core.TokenListABC):
                decl_storage_list = None
                decl_type = None
                decl_name = decl
                decl_array_size = None
                decl_initializer = None

            else:
                raise ValueError("Cannot create a Var from "+str(builtins.type(decl)))
            
        # If decl was None
        else:
            decl_storage_list = None
            decl_type = None
            decl_name = None
            decl_array_size = None
            decl_initializer = None            
        
        # User gave a declaration and specified some other parameters
        # The explicitly specified parameters have higher priority
        storage_list = decl_storage_list if storage_list is None else (
            storage_list.split() if isinstance(storage_list, str) else storage_list
        )
        type = decl_type if type is None else type
        name = decl_name if name is None else name
        array_size = decl_array_size if array_size is None else array_size            
        initializer = decl_initializer if initializer is None else initializer
            
            
        self.storage_list = storage_list
        self.type = type
        self.name = name
        self.array_size = array_size
        self.initializer = initializer
        
        # Store the name in the token_list member to allow Expr magic
        super().__init__(tokenlist_attr_name='name', *args, **kwargs)
    
    def freestanding_str(self, idt=None):
        return self.defi().freestanding_str(idt)

    def decl(self):
        return VarDecl(self)

    def defi(self):
        return VarDefi(self)
    
    def extern_decl(self):
        return VarExternDecl(self)

    def __getitem__(self, key):
        return Expr((self,"[",key,"]"))

class VarDecl(NodeView, core.NonIterable):
    # Regex used to match type names using stars (pointers) and adjust spaces
    star_space_handling_regex = re.compile('^\s*(?P<name>[^\*]*)(\s)*(?P<stars>\*+)\s*$')

    def freestanding_str(self, idt=None, hide_initializer=False, hide_array_size=False):
        idt = core.Indentation.make_idt(idt)
        return '\n'+str(idt)+self.inline_str(idt, hide_initializer=hide_initializer, hide_array_size=hide_array_size)+';'+self.side_comment.inline_str(idt)

    def inline_str(self, idt=None, hide_initializer=False, hide_array_size=False):
        storage_list = " ".join(storage.inline_str(idt) for storage in self.parent.storage_list)+" "
        snippet = storage_list.strip()+" "

        if self.parent.type is not None:
            if self.parent.array_size is not None:
                snippet += self.parent.type.inline_str(idt)+" "
                snippet += self.parent.inline_str(idt)
                if not hide_array_size:
                    array_size_str = self.parent.array_size.inline_str(idt)
                else:
                    array_size_str = ''
                snippet += "["+array_size_str+"]"

            else:
                type_str = self.parent.type.inline_str(idt)
                # See if there is any whitespace changes to apply
                match_obj = self.star_space_handling_regex.match(type_str)
                if match_obj:
                    name = match_obj.group('name') if match_obj.group('name') is not None else ''
                    stars = match_obj.group('stars') if match_obj.group('stars') is not None else ''
                    type_str = name.strip()+' '+stars.strip()
                    
                # Add a space between the type name and the variable, but only if this is 
                # not a pointer, in which case the space is between the type name and the stars
                type_addend = '' if type_str.endswith('*') else " "
                snippet += type_str+type_addend
                snippet += self.parent.inline_str(idt)
        else:
                snippet += self.parent.inline_str(idt)

        if not hide_initializer and self.parent.initializer is not None:
            snippet += " = "+self.parent.initializer.inline_str(idt)

        return snippet.strip()

class VarDefi(VarDecl):
    pass

class VarExternDecl(VarDecl):
    def __init__(self, var, hide_initializer=True, hide_array_size=True, *args, **kwargs):
        self.hide_initializer=hide_initializer
        self.hide_array_size = hide_array_size
        super().__init__(var, *args, **kwargs)
        
    def inline_str(self, idt=None, hide_initializer=None, hide_array_size=None):
        if hide_initializer is None:
            hide_initializer = self.hide_initializer
        if hide_array_size is None:
            hide_array_size = self.hide_array_size
            
        return "extern "+super().inline_str(idt, hide_initializer=hide_initializer, hide_array_size=hide_array_size)
    
    def freestanding_str(self, idt=None, hide_initializer=None, hide_array_size=None):
        if hide_initializer is None:
            hide_initializer = self.hide_initializer
        if hide_array_size is None:
            hide_array_size = self.hide_array_size
        
        return super().freestanding_str(idt, hide_initializer=hide_initializer, hide_array_size=hide_array_size)


class Fun(BlockStmt):
    name = core.EnsureNode('name', TokenList)
    return_type = core.EnsureNode('return_type', TokenList)
    storage_list = core.EnsureNode('storage_list', TokenListContainer)
    param_list = core.EnsureNode('param_list', TokenListContainer)

    
    def __init__(self, name=None, return_type="void", storage_list=None, param_list=None, *args, **kwargs):
        self.name = name
        self.return_type = return_type
        self.storage_list = storage_list
        self.param_list = param_list
        super().__init__(*args, **kwargs)

    def inline_str(self, idt=None):
        return self.defi().inline_str(idt)

    def __call__(self, *args):
        return self.call(args)

    def defi(self):
        return FunDef(self)
        
    def decl(self):
        return FunDecl(self)

    def call(self, param_list=None):
        return FunCall(self, param_list)

class FunParam(Var):
    def inline_str(self, idt=None):
        return self.decl().inline_str(idt)

class FunDef(NodeView):
    __format_string = "{idt_nl}{storage_list}{type}{name}({param_list}){side_comment}{body}"

    def inline_str(self, idt=None):
        storage_list = " ".join(storage.inline_str(idt) for storage in self.parent.storage_list)+" "
        storage_list = storage_list.strip()
        if storage_list:
            storage_list += ' '

        param_list = ", ".join(param.inline_str(idt) for param in self.parent.param_list)
        param_list = param_list.strip()
        if not param_list:
            param_list = "void"

        return self.__format_string.format(
            type = self.parent.return_type.inline_str(idt)+' ',
            name = self.parent.name.inline_str(idt),
            param_list = param_list,
            side_comment = self.parent.side_comment.inline_str(idt),
            storage_list = storage_list,
            body = super(Fun, self.parent).inline_str(idt),
            idt_nl = '\n'+str(idt)
        )

class FunDecl(NodeView):
    __format_string = "{storage_list}{type}{name}({param_list});{side_comment}"

    def inline_str(self, idt=None):
        storage_list = " ".join(storage.inline_str(idt) for storage in self.parent.storage_list)+" "
        storage_list = storage_list.strip()
        if storage_list:
            storage_list += ' '
        
        param_list = ", ".join(param.inline_str(idt) for param in self.parent.param_list)
        param_list = param_list.strip()
        if not param_list:
            param_list = "void"

        return self.__format_string.format(
            type = self.parent.return_type.inline_str(idt)+' ',
            name = self.parent.name.inline_str(idt),
            param_list = param_list,
            storage_list = storage_list,
            side_comment = self.side_comment.inline_str(idt)
        )

class FunCall(NodeView, Expr, core.NonIterable):
    param_list = core.EnsureNode('param_list', TokenListContainer)
    param_joiner = ', '
    
    __format_string = "{name}({param_list})"

    def __init__(self, parent, param_list=None, param_joiner=None, *args, **kwargs):
        self.param_list = param_list
        if param_joiner is not None:
            self.param_joiner = param_joiner
        super().__init__(self, parent=parent, *args, **kwargs)

    def inline_str(self, idt=None):
        return self.__format_string.format(
            name = self.parent.name.inline_str(idt),
            param_list = self.param_joiner.join(param.inline_str(idt) for param in self.param_list),
        )

class Type(DelegatedTokenList, core.NonIterable):
    name = core.EnsureNode('name', TokenList)
    array_size = core.EnsureNode('array_size ',
        node_factory=lambda array_size: TokenList(array_size) if array_size is not None else None,
        node_classinfo=TokenList
    )
    
    type_declaration_regex = re.compile('^\s*(?P<name>.*?)\s*(\[\s*(?P<array_size>.*?)\s*\])\s*$')
    
    def __init__(self, name=None, array_size=None, *args, **kwargs):
        match = self.type_declaration_regex.match(name) if isinstance(name, str) else None
        if match:
            self.name = match.group('name')
            self.array_size = match.group('array_size')
            if array_size is not None:
                self.array_size = array_size
        else:
            self.name = name
            self.array_size = array_size
        super().__init__(tokenlist_attr_name='name', *args, **kwargs)


class TypePointer(NodeView):   
    def inline_str(self, idt=None):
        return self.parent.inline_str(idt)+'*'

class CompoundType(BlockStmt):
    name = core.EnsureNode('name', TokenList)
    
    def __init__(self, name=None, auto_typedef=True, *args, **kwargs):
        self.name = name
        self.auto_typedef = auto_typedef
        super().__init__(*args, **kwargs)

    def anonymous(self):
        return CompoundTypeAnonymousView(self)

    def inline_str(self, idt=None):
        return self.name.inline_str(idt)
    
    def freestanding_str(self, idt=None):
        idt = core.Indentation.make_idt(idt)
        if self.auto_typedef:
            format_string = self.__typedef_format_string
        else:
            format_string = self.__format_string
        
        # The format string do not contain the newline and indentation
        # at their beginning to be consistent with the format string of
        # other classes
        format_string = '\n\n'+str(idt)+format_string
       
        return format_string.format(
            name = self.name.inline_str(idt),
            members = super().inline_str(idt),  
            side_comment = self.side_comment.inline_str(idt),
            idt_nl = '\n'+str(idt)
        )
    
    def forward_decl(self):
        return CompoundTypeForwardDeclaration(self)
    
    def ptr(self):
        return TypePointer(self)
    
    def __pos__(self):
        return self.ptr()

class CompoundTypeAnonymousView(NodeView):
    def inline_str(self, idt=None):
        return (self.parent.__prefix_string+' {'+
            self.parent.__separator_string.join(
                member.decl().inline_str()
                for member in self.parent
                )+
            self.parent.__separator_string.rstrip()+'}')
            
class CompoundTypeForwardDeclaration(NodeView, core.NonIterable):    
    def inline_str(self, idt=None):
        idt = core.Indentation.make_idt(idt)
        format_string = self.parent._CompoundType__forward_declaration_format_string
        if self.parent.auto_typedef:
            format_string += '{idt_nl}'+self.parent._CompoundType__forward_declaration_typedef_format_string
            
        return format_string.format(
            name = self.parent.name.inline_str(idt),
            side_comment = self.side_comment.inline_str(idt),
            idt_nl = '\n'+str(idt)
        )            
    
class EnumMember(Var):
    def __init__(self, *args, **kwargs):
        self.is_last_member = False
        super().__init__(*args, **kwargs)
        # Remove any sort of type or array_size after the object is constructed
        self.type = None
        self.array_size = None
        
    def freestanding_str(self, idt=None):
        idt = core.Indentation.make_idt(idt)
        # Stateful hack to avoid printing a trailing comma in enumeration
        # is_last_member state is restored by Enum class when printing is done
        if self.is_last_member:
            addend = ''
        else:
            addend = ','
            
        return '\n'+str(idt)+self.decl().inline_str(idt)+addend+self.side_comment.inline_str(idt)
        
class Enum(CompoundType):
    _CompoundType__typedef_format_string = "typedef enum {name}{members} {name};{side_comment}"
    _CompoundType__format_string = "enum {name}{members};{side_comment}"
    _CompoundType__forward_declaration_format_string = "enum {name};{side_comment}"
    _CompoundType__forward_declaration_typedef_format_string = "typedef enum {name} {name};"
    _CompoundTypeAnonymousView__prefix_string = 'enum'
    _CompoundTypeAnonymousView__separator_string = ', '
    
    def __init__(self, name=None, member_list=None, auto_typedef=True, *args, **kwargs):
        super().__init__(name, auto_typedef, node_list=member_list, node_classinfo=EnumMember, *args, **kwargs)
        
    def freestanding_str(self, idt=None):
        # If there is at least one enumerator, so we can take the last member because it exists
        if self:
            last_member = self[-1]
            is_last_member_value = last_member.is_last_member
            try:
                last_member.is_last_member = True
                snippet = super().freestanding_str(idt)
            finally:
                # Restore the old value in case we want to append another
                # enumerator after we printed the enum once
                last_member.is_last_member = is_last_member_value
        else:
            snippet = super().freestanding_str(idt)

        return snippet
    
class StructMember(Var):    
    @property
    def initializer(self):
        """Special handling of initializer here: if the initializer is gotten, 
        None is returned, to avoid displaying it in the structure declaration.
        If set, the content is redirected to default_initializer attribute, 
        to allow building of a default designated initializer.
        """
        return None
    
    @initializer.setter
    def initializer(self, value):
        # Make sure it is a TokenList, as EnsureNode would do for
        # the initializer attribute of the Var class.
        value = TokenList.ensure_node(value)
        self.default_initializer = value
    

class UnionMember(Var):
    pass

class _StructUnionBase(CompoundType):
    _CompoundTypeAnonymousView__separator_string = '; '

class Struct(_StructUnionBase):
    _CompoundType__typedef_format_string = "typedef struct {name}{members} {name};{side_comment}"
    _CompoundType__format_string = "struct {name}{members};{side_comment}"
    _CompoundType__forward_declaration_format_string = "struct {name};{side_comment}"
    _CompoundType__forward_declaration_typedef_format_string = "typedef struct {name} {name};"
    _CompoundTypeAnonymousView__prefix_string = 'struct'
    
    def __init__(self, name=None, member_list=None, auto_typedef=True, *args, **kwargs):
        super().__init__(name, auto_typedef, node_list=member_list, node_classinfo=(StructMember), *args, **kwargs)
    
    def designated_init(self):
        return StructDefaultDesignatedInitializer(self)

class StructDesignatedInitializer(Expr, collections.MutableMapping):
    default_translation_map = {int: 'int', float: 'float', str:'char *'}
    
    def __init__(self, value_map=None, *args, **kwargs):
        self.value_map = collections.OrderedDict()
        
        if isinstance(value_map, collections.Mapping):
            for key, value in value_map.items():
                self[key] = TokenList.ensure_node(value)
        
        super().__init__(*args, **kwargs)

    def inline_str(self, idt=None):
        # Filter out the members that do not have any initializer
        snippet = '{'+', '.join(
            '.'+TokenList(member).inline_str()+'='+value.inline_str()
            for member,value in self.value_map.items() if value.inline_str()
        )+'}'
        
        return snippet
    
    def struct(self, name=None, auto_typedef=True, type_translation_map=None):
        
        def default_translator(type_translation_map, value):
            """This translator uses the type_translation_map as a mapping
            of Python types to C types (strings).
            """
            # TokenList are treated as a special case: we decapsulate
            # the first token to find its type
            if isinstance(value, core.TokenListABC):
                return type_translation_map[type(value[0])]
            else:
                return type_translation_map[type(value)]

        if callable(type_translation_map):
            translate_type = type_translation_map
        elif isinstance(type_translation_map, collections.Mapping):
            # The translator compare the first token in TokenList, because
            # values are always instances of TokenList
            translate_type = lambda value: default_translator(type_translation_map, value)
        elif type_translation_map is None:
            translate_type = lambda value: default_translator(self.default_translation_map, value)
        else:
            raise ValueError('type_translation_map must be either callable or a mapping')
        
        struct = Struct(
            name = name,
            auto_typedef = auto_typedef,
            side_comment = self.side_comment,
            comment = self.comment
        )

        for member, value in self.items():
            # If there is a nested designated intializer, output an anonymous 
            # struct type for the member
            if isinstance(value, StructDesignatedInitializer):
                type_ = value.struct(type_translation_map=type_translation_map).anonymous()
            else:
                type_ = translate_type(value) 
                
            struct.append(StructMember(
                name = member,
                # Set the initializer, so we can use Struct.designated_init() on the resulting structure
                initializer = value,
                type = type_
            ))
            
        return struct
    
    def __getitem__(self, key):
        # If the key is a string, try to catch any reference
        # to a nested member, and forward it to the nested
        # StructDesignatedInitializer instance
        if isinstance(key, str):
            split_key = key.split('.')
            if len(split_key) > 1:
                nested_member = '.'.join(split_key[1:])
                return self.value_map[split_key[0]][nested_member]
            return self.value_map[key]
        else:
            return self.value_map[key]
    
    def __setitem__(self, key, value):
        value = TokenList.ensure_node(value)
        # If the key is a string, try to catch any reference
        # to a nested member, and forward it to the nested
        # StructDesignatedInitializer instance        
        if isinstance(key, str):
            split_key = key.split('.')
            if len(split_key) > 1:
                nested_member = '.'.join(split_key[1:])
                self.value_map.setdefault(split_key[0], StructDesignatedInitializer())[nested_member] = value
            else:
                self.value_map[key] = value
        else:
            self.value_map[key] = value

    def __copy__(self):
        cls = type(self)
        new_obj = cls.__new__(cls)
        new_obj.__dict__.update(self.__dict__)
        new_obj.value_map = copy.copy(self.value_map)
        return new_obj

        
    def __delitem__(self, key):
        del self.value_map[key]
        
    def __len__(self):
        return len(self.value_map)
    
    def __iter__(self):
        return iter(self.value_map)
    
class StructDefaultDesignatedInitializer(NodeView, StructDesignatedInitializer):   
    def inline_str(self, idt=None):
        merged_initializer = collections.OrderedDict(
            [(member.inline_str(),member.default_initializer)
            for member in self.parent.node_list]+
            list(self.items())
        )
        return StructDesignatedInitializer(merged_initializer).inline_str(idt)
        

class Union(_StructUnionBase):
    _CompoundType__typedef_format_string = "typedef union {name}{members} {name};{side_comment}"
    _CompoundType__format_string= "union {name}{members};{side_comment}"
    _CompoundType__forward_declaration_format_string = "union {name};{side_comment}"
    _CompoundType__forward_declaration_typedef_format_string = "typedef union {name} {name};"
    _CompoundTypeAnonymousView__prefix_string = 'union'
    
    def __init__(self, name=None, member_list=None, auto_typedef=True, *args, **kwargs):
        super().__init__(name, auto_typedef, node_list=member_list, node_classinfo=(UnionMember,core.NodeABC), *args, **kwargs)
    

class Typedef(Node, core.NonIterable):
    old_name = core.EnsureNode('old_name', TokenList)
    name = core.EnsureNode('name', TokenList)
    
    __format_string = "typedef {old_name} {new_name};{side_comment}"

    def __init__(self, old_name=None, new_name=None, *args, **kwargs):
        self.old_name = old_name
        self.name = new_name
        super().__init__(*args, **kwargs)

    def inline_str(self, idt=None):
        return self.name.inline_str(idt)

    def freestanding_str(self, idt=None):
        idt = core.Indentation.make_idt(idt)
        format_string = '\n'+str(idt)+self.__format_string
        return format_string.format(
            old_name = self.old_name.inline_str(idt),
            new_name = self.name.inline_str(idt),
            side_comment = self.side_comment.inline_str(idt)
        )


class FunPtrTypedef(DelegatedTokenList, core.NonIterable):
    name = core.EnsureNode('name', TokenList)
    param_list = core.EnsureNode('param_list', TokenListContainer)
    return_type = core.EnsureNode('return_type', TokenList)
     
    __format_string = "typedef {return_type} (*{name})({param_list});{side_comment}"

    def __init__(self, name=None, return_type=None, param_list=None, *args, **kwargs):
        self.name = name
        self.param_list = param_list
        self.return_type = return_type
        super().__init__(tokenlist_attr_name='name', *args, **kwargs)
    
    def freestanding_str(self, idt=None):
        idt = core.Indentation.make_idt(idt)
        format_string = '\n'+str(idt)+self.__format_string        
        return format_string.format(
            name = self.parent.name.inline_str(idt),
            return_type = self.parent.return_type.inline_str(idt),
            param_list = ", ".join(param.inline_str(idt) for param in self.parent.param_list),
            side_comment = self.side_comment.inline_str(idt)
        )

class OneLinePrepBase(Node, core.NonIterable):
    directive = core.EnsureNode('directive', TokenList)
    param_list = core.EnsureNode('param_list', TokenListContainer)
    
    __format_string = "#{directive} {param_list}{side_comment}"

    def __init__(self, directive=None, param_list=None, *args, **kwargs):
        self.directive = directive
        self.param_list = param_list
        super().__init__(*args, **kwargs)
        
    def inline_str(self, idt=None):
        param_list = " ".join(param.inline_str(idt) for param in self.param_list)
        
        return self.__format_string.format(
            directive = self.directive.inline_str(idt),
            param_list = param_list,
            side_comment = self.side_comment.inline_str(idt)
        )
        

class PrepDef(OneLinePrepBase):
    name = core.EnsureNode('name', TokenList)
    value = core.EnsureNode('value', TokenList)
    
    def __init__(self, name=None, value=None, *args, **kwargs):
        self.name = name
        self.value = value
        super().__init__("define", (core.NodeAttrProxy(self, 'name'), core.NodeAttrProxy(self, 'value')), *args, **kwargs)


class PrepInclude(OneLinePrepBase):
    header_path = core.EnsureNode('header_path', TokenList)
    
    def __init__(self, header_path=None, system=False, *args, **kwargs):
        
        self.header_path = header_path
        header_path_proxy = core.NodeAttrProxy(self, 'header_path')

        if system:
            processed_path = TokenList(('<', header_path_proxy, '>'))
        else:
            processed_path = TokenList(('"', header_path_proxy, '"'))

        super().__init__("include", [processed_path], *args, **kwargs)
    
            
class PrepIf(StmtContainer):
    cond = core.EnsureNode('cond', TokenList)
    
    __format_string = "#if {cond}{side_comment}{stmt}{idt_nl}#endif //{cond}"
    
    def __init__(self, cond=None, indent_content=False, *args, **kwargs):
        self.cond = cond
        self.indent_content = indent_content
        super().__init__(*args, **kwargs)

    def inline_str(self, idt=None):
        idt = core.Indentation.make_idt(idt)
        if self.indent_content:
            stmt_idt = copy.copy(idt)
            stmt_idt.indent()
        else:
            stmt_idt = idt
        return self.__format_string.format(
            cond = self.cond.inline_str(idt),
            stmt = super().inline_str(stmt_idt),
            side_comment = self.side_comment.inline_str(idt),
            idt_nl = '\n'+str(idt)
        )

class PrepIfDef(PrepIf):
    _PrepIf__format_string = "#ifdef {cond}{side_comment}{stmt}{idt_nl}#endif //ifdef {cond}"

class PrepIfNDef(PrepIf):
    _PrepIf__format_string = "#ifndef {cond}{side_comment}{stmt}{idt_nl}#endif //ifndef {cond}"


class BaseCom(Node, core.NonIterable):
    pass

class Com(TokenListContainer, BaseCom):
    # String put at the front of the comment
    start_string = '/* '
    # String put at the end of the comment
    end_string = ' */'
    # Maximum line length when auto_wrap is enabled
    max_line_length = 80
    
    def __init__(self, node_list=None, auto_wrap=True, *args, **kwargs):
        self.auto_wrap = auto_wrap
        super().__init__(node_list, *args, **kwargs)
    
    def inline_str(self, idt=None):
        idt = core.Indentation.make_idt(idt)
        string = "\n".join(comment.inline_str(idt) for comment in self)
        if not string:
            return ''
        
        split_string = string.split("\n")
        first_line = split_string [0]
        last_line = split_string [-1]
        # If the first line is not empty, add a few spaces to indentation to
        # align the paragraphs correctly
        if first_line.strip():
            sub_idt = len(self.start_string)*" "
            start_string = self.start_string
        else:
            sub_idt = ""
            start_string = self.start_string.strip()
        joiner = "\n"+str(idt)+sub_idt   
        
        
        if last_line.strip():
            end_string = self.end_string
        else:
            end_string = self.end_string.strip()
        
        # If the comment cannot fit on a single line and auto wrapping is enabled
        if self.auto_wrap and any(
            len(line) > self.max_line_length-len(start_string)-len(end_string)-len(str(idt))
            for line in split_string
        ):
            string = "\n".join(textwrap.wrap(
                string,
                width=self.max_line_length,
                expand_tabs=False,
                replace_whitespace=False,
            ))
                    
        string = start_string+string+end_string+self.side_comment.inline_str(idt)
        string = string.replace("\n", joiner)
            
        return string 

    def freestanding_str(self, idt=None):
        idt = core.Indentation.make_idt(idt)
        return '\n\n'+str(idt)+self.inline_str(idt)

class SingleLineCom(DelegatedTokenList, BaseCom):
    content = core.EnsureNode('content', TokenList)

    start_string = ' //'
    
    def __init__(self, comment=None, *args, **kwargs):
        self.content = comment
        super().__init__(tokenlist_attr_name='content', *args, **kwargs)
    
    def inline_str(self, idt=None):
        content_string = super().inline_str(idt)
        return self.start_string+content_string
        
    freestanding_str = inline_str

    
class NewLine(Node):
    def inline_str(self, idt=None):
        idt = core.Indentation.make_idt(idt)
        return '\n'+str(idt)
    
    freestanding_str = inline_str
        

class HeaderFile(PrepIfNDef):
    include_guard_define = core.EnsureNode('include_guard_define', TokenList)
    
    def __init__(self, filename=None, include_guard=None, template=None, node_list=None, *args, **kwargs):
        if include_guard is None and filename is not None:
            self.include_guard_define = core.format_string(filename, 'UPPER_UNDERSCORE_CASE')+'_H_'
        else:
            self.include_guard_define = include_guard
            
        node_list = core.listify(node_list)+[PrepDef(self.include_guard_define)]
        
        super().__init__(core.NodeAttrProxy(self, 'include_guard_define'), indent_content=False, node_list=node_list, *args, **kwargs)
        
        
        