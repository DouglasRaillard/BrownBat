
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
import textwrap
import re
import builtins
import inspect
import os
import copy

import brownbat.core as core

class Configuration:
    def __init__(self, enable_debug_comments):
        self.enable_debug_comments = enable_debug_comments

default_config = Configuration(
    enable_debug_comments = False
)

class Node(core.NodeBase):
    config = default_config
    
    # We must check if the comment is None to avoid infinite recursion
    # because Com tries to build a TokenList (via TokenListContainer) with comment=None, which in turn
    # tries to build a comment with None and so on
    comment = core.EnsureNode('comment', lambda x: Com(x) if x is not None else core.phantom_node)
    # We must check if the comment is None to avoid infinite recursion
    # because SingleLineCom tries to build a TokenList with comment=None, which in turn
    # tries to build a comment with None and so on
    side_comment = core.EnsureNode('side_comment', lambda x: SingleLineCom(x) if x is not None else core.phantom_node)
        
    def __init__(self, comment=None, side_comment=None, parent=None, config=None):
        if config is not None:
            self.config = config
        
        # /!\ Be carefull here: as this class is the base class of all classes
        # in this file, any constructor call here will turn into infinite
        # recursion. Fortunately, side_comment is irrelevant for Backtrace
        if self.config.enable_debug_comments and not isinstance(self, (Backtrace, SingleLineCom)):
            side_comment = SingleLineCom((self.__class__.__name__+' created at '+Backtrace()))
            
        super().__init__(comment=comment, side_comment=side_comment, parent=parent)

class NodeView(core.NodeViewBase, Node):
    side_comment = core.DelegateAttribute(
        'side_comment', 'parent',
        descriptor = Node.side_comment,
        default_value_list = (None,)
    )
    
    comment = core.DelegateAttribute(
        'comment', 'parent',
        descriptor = Node.comment,
        default_value_list = (None,)
    )

class NodeContainer(core.NodeContainerBase, Node):
    def __add__(self, other):
        # TokenListContainer are the most agnostic containers
        return TokenListContainer((self, other))
    
    def __radd__(self, other):
        # TokenListContainer are the most agnostic containers
        return TokenListContainer((other, self))
    

class TokenListContainer(NodeContainer):
    def __init__(self, *args, **kwargs):
        super().__init__(node_classinfo=TokenList, *args, **kwargs)

class TokenList(core.TokenListBase, Node):
    pass

class DelegatedTokenList(core.DelegatedTokenListBase, Node):
    pass

class IndentedTokenList(core.IndentedTokenListBase, TokenList):
    pass

class IndentedDelegatedTokenList(core.IndentedDelegatedTokenListBase, DelegatedTokenList):
    pass

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
        return Expr((self," = ",TokenList.ensure_node(value)))
    
    def cast(self, new_type):
        return Expr(('((',TokenList.ensure_node(new_type),')(',self,'))'))

class Expr(_Expr, IndentedTokenList):
    pass

class DelegatedExpr(_Expr, IndentedDelegatedTokenList):
    pass
    

class StmtContainer(NodeContainer, core.NonSequence):
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
        
    
class ConditionnalStmt(BlockStmt):
    cond = core.EnsureNode('cond', TokenList)
    
    def __init__(self, cond=None, *args, **kwargs):
        self.cond = cond
        super().__init__(*args, **kwargs)

    def inline_str(self, idt=None):
        return self.__format_string.format(
            cond = self.cond.inline_str(idt),
            stmt = super().inline_str(idt),
            side_comment = self.side_comment.inline_str(idt),
            idt_nl = '\n'+str(idt)
        )


class If(ConditionnalStmt):
    _ConditionnalStmt__format_string = "if({cond}){side_comment}{stmt}"
    
class Else(ConditionnalStmt):
    _ConditionnalStmt__format_string = "else{side_comment}{stmt}"
    
    def __init__(self, *args, **kwargs):
        super().__init__(cond=None, *args, **kwargs)
    
class ElseIf(ConditionnalStmt):
    _ConditionnalStmt__format_string = "else if({cond}){side_comment}{stmt}"
    
class While(ConditionnalStmt):
    _ConditionnalStmt__format_string = "while({cond}){side_comment}{stmt}"

class For(BlockStmt):
    init = core.EnsureNode('init', TokenList)
    cond = core.EnsureNode('cond', TokenList)
    action = core.EnsureNode('action', TokenList)

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
    cond = core.EnsureNode('cond', TokenList)

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

class Switch(Node, core.NonSequence, collections.MutableMapping):
    expr = core.EnsureNode('expr', TokenList)
    
    __format_string = "switch({expr}){side_comment}{idt_nl}{{{stmt}{idt_nl}}}"
    __case_format_string = "{idt_nl}case ({case}):{side_comment}{stmt}{auto_break}\n"
    __default_format_string = "{idt_nl}default:{side_comment}{stmt}{auto_break}\n"

    def __init__(self, expr=None, case_map=None, auto_break=True, *args, **kwargs):
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

    array_size = core.EnsureNode('array_size',
        node_factory=lambda array_size: TokenList(array_size) if array_size is not None else None,
        node_classinfo=TokenList
    )
    initializer = core.EnsureNode('initializer',
        node_factory=lambda initializer: TokenList(initializer) if initializer is not None else None,
        node_classinfo=TokenList
    )
    
    c_identifier_regex_str = "[a-zA-Z_]+[a-zA-Z0-9_]*"
    var_defi_name_array_initializer_regex_str = "(?:(?P<name>"+c_identifier_regex_str+")\s*)(?:\[\s*(?P<array_size>.*?)\s*\])?(?:\s*=\s*(?P<initializer>.*?)\s*)?"
    var_defi_storage_list_regex_str = "(?P<storage_list>.*?)"
    var_def_type_regex_str = "(?P<type>(?:(?P<_is_a_compound>union|struct|enum)\s*(?(_is_a_compound)(?:(?:\{.*?\})|(?:"+c_identifier_regex_str+"))|"+c_identifier_regex_str+"))?(?(_is_a_compound)|"+c_identifier_regex_str+")(?:\s*\*)?)"
        
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
                if decl_type is not None and decl_type.endswith('*'):
                    decl_type = decl_type[:-1].strip()+' *'
                    
                decl_name = match.group('name')
                
                decl_array_size = match.group('array_size')
                # Replace empty array size with 0
                if decl_array_size is not None:
                    decl_array_size = decl_array_size if decl_array_size else 0
                    
                decl_initializer = match.group('initializer')
            
            # Make a shallow copy of the other Var
            elif isinstance(decl, Var):
                decl_storage_list = decl.storage_list
                decl_type = decl.type
                decl_name = decl
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
        if self.array_size is None:
            raise KeyError("This variable is not an array")

        return Expr((self,"[",key,"]"))

class VarDecl(NodeView, core.NonSequence):
    
    def __init__(self, var, *args, **kwargs):
        self.parent = var
        super().__init__(*args, **kwargs)


    def freestanding_str(self, idt=None):
        idt = core.Indentation.make_idt(idt)
        return '\n'+str(idt)+self.inline_str(idt)+';'+self.side_comment.inline_str(idt)

    def inline_str(self, idt=None):
        storage_list = " ".join(storage.inline_str(idt) for storage in self.parent.storage_list)+" "
        snippet = storage_list.strip()+" "

        if self.parent.type is not None:
            if self.parent.array_size is not None:
                try:
                    array_size_as_int = int(self.parent.array_size.inline_str(idt))                    
                except ValueError:
                    array_size_as_int = 1

                snippet += self.parent.type.inline_str(idt)+" "
                snippet += self.parent.inline_str(idt)
                snippet += "["+self.parent.array_size.inline_str(idt)+"]"

            else:
                type_str = self.parent.type.inline_str(idt)
                type_addend = '' if type_str.endswith(' *') else " "
                snippet += type_str+type_addend
                snippet += self.parent.inline_str(idt)
        else:
                snippet += self.parent.inline_str(idt)

        if self.parent.initializer is not None:
            snippet += " = "+self.parent.initializer.inline_str(idt)

        return snippet.strip()

class VarDefi(VarDecl):
    pass

class VarExternDecl(VarDecl):
    def inline_str(self, idt=None):
        return "extern "+super().inline_str(idt)


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
    
    def __init__(self, function, *args, **kwargs):
        self.parent = function
        super().__init__(*args, **kwargs)

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

    def __init__(self, function, *args, **kwargs):
        self.parent = function
        super().__init__(*args, **kwargs)

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

class FunCall(NodeView, Expr, core.NonSequence):
    param_list = core.EnsureNode('param_list', TokenListContainer)
    param_joiner = ', '
    
    __format_string = "{name}({param_list})"

    def __init__(self, function, param_list=None, param_joiner=None, *args, **kwargs):
        self.parent = function
        self.param_list = param_list
        if param_joiner is not None:
            self.param_joiner = param_joiner
        super().__init__(self, *args, **kwargs)

    def inline_str(self, idt=None):
        return self.__format_string.format(
            name = self.parent.name.inline_str(idt),
            param_list = self.param_joiner.join(param.inline_str(idt) for param in self.param_list),
        )

# This is not for inheritance inside this library, only a helper for final user
class Type(DelegatedTokenList, core.NonSequence):
    name = core.EnsureNode('name', TokenList)
    
    def __init__(self, name=None, *args, **kwargs):
        self.name = name
        super().__init__(tokenlist_attr_name='name', *args, **kwargs)



class CompoundType(BlockStmt):
    name = core.EnsureNode('name', TokenList)
    
    def __init__(self, name=None, auto_typedef=True, *args, **kwargs):
        self.name = name
        self.auto_typedef = auto_typedef
        super().__init__(*args, **kwargs)

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
        format_string = '\n'+str(idt)+format_string
       
        return format_string.format(
            name = self.name.inline_str(idt),
            members = super().inline_str(idt),  
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
    
class _StructUnionMember(Var):
    pass

class StructMember(_StructUnionMember):
    pass

class UnionMember(_StructUnionMember):
    pass

class _StructUnionBase(CompoundType):
    def __init__(self, name=None, member_list=None, auto_typedef=True, *args, **kwargs):
        super().__init__(name, auto_typedef, node_list=member_list, node_classinfo=(_StructUnionMember,core.NodeABC), *args, **kwargs)
   

class Struct(_StructUnionBase):
    _CompoundType__typedef_format_string = "typedef struct {name}{members} {name};{side_comment}"
    _CompoundType__format_string = "struct {name}{members};{side_comment}"


class Union(_StructUnionBase):
    _CompoundType__typedef_format_string = "typedef union {name}{members} {name};{side_comment}"
    _CompoundType__format_string= "union {name}{members};{side_comment}"
    

class Typedef(Node, core.NonSequence):
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


class FunPtrTypedef(DelegatedTokenList, core.NonSequence):
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

class Prep(Node, core.NonSequence):
    directive = core.EnsureNode('directive', TokenList)
    param_list = core.EnsureNode('param_list', TokenListContainer)
    
    __format_string = "#{directive} {param_list}{side_comment}"

    def __init__(self, directive=None, param_list=None, *args, **kwargs):
        self.directive = directive
        self.param_list = core.listify(param_list)
        super().__init__(*args, **kwargs)
        
    def inline_str(self, idt=None):
        param_list = " ".join(param.inline_str(idt) for param in self.param_list)
        
        return self.__format_string.format(
            directive = self.directive.inline_str(idt),
            param_list = param_list,
            side_comment = self.side_comment.inline_str(idt)
        )
        

class PrepDef(Prep):
    def __init__(self, name=None, value=None, *args, **kwargs):
        self.name = name
        self.value = value
        super().__init__("define", (core.NodeAttrProxy(self, 'name'), core.NodeAttrProxy(self, 'value')), *args, **kwargs)

    def inline_str(self, idt=None):
        return self.param_list[0].inline_str(idt)

class PrepInclude(Prep):
    def __init__(self, header_path=None, system=False, *args, **kwargs):
        
        self.header_path = TokenList(header_path)
        header_path_proxy = core.NodeAttrProxy(self, 'header_path')

        if system:
            processed_path = TokenList(('<', header_path_proxy, '>'))
        else:
            processed_path = TokenList(('"', header_path_proxy, '"'))

        super().__init__("include", processed_path, *args, **kwargs)
    
            
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

class BaseCom(Node, core.NonSequence):
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
        
        first_line = string.split("\n")[0]
        last_line = string.split("\n")[-1]
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
        if self.auto_wrap and len(first_line) > self.max_line_length-len(start_string)-len(end_string)-len(str(idt)):
            string = "\n".join(textwrap.wrap(
                string,
                width=self.max_line_length,
                expand_tabs=False,
                replace_whitespace=False,
            ))
                    
        string = start_string+string+end_string+self.side_comment.inline_str(idt)
        string = string.replace("\n", joiner)
            
        return string 

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

    
class Backtrace(TokenList, core.NonSequence):
    __frame_format_string = '{filename}:{lineno}({function})'
    __frame_joiner = ', '
    
    def __init__(self, level=0, *args, **kwargs):
        stack = inspect.stack()
        self.stack_frame_list = [
            frame[1:] for frame in stack
            if os.path.dirname(frame[1]) != os.path.dirname(__file__)
        ]

        super().__init__(self, *args, **kwargs)
        
    def freestanding_str(self, idt=None):
        return SingleLineCom(('Object built at ', self)).freestanding_str(idt)

    def self_inline_str(self, idt=None):
        return self._Backtrace__frame_joiner.join(
            self._Backtrace__frame_format_string.format(
                filename = os.path.relpath(frame[0]),
                lineno = frame[1],
                function = frame[2],
                line_content = frame[3][frame[4]] if frame[3] is not None else ''
            ) for frame in self.stack_frame_list
        )

class NewLine(Node):
    def inline_str(self, idt=None):
        idt = core.Indentation.make_idt(idt)
        return '\n'+str(idt)
    
    freestanding_str = inline_str
        
