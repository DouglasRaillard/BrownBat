#! /usr/bin/python3
# -*-coding:Utf-8 -*


import traceback
import collections

import sys
# If BrownBat is not installed, this enable the example to be run from the root of the project or this directory
sys.path[0:0] = ['.', '..']


import brownbat.C as C
import brownbat.core as core


class Name(C.TokenList):
    name_list = []
    module_name = "foo"
    convention_applied = False
    
    def __init__(self, token_list=None):
        Name.name_list.append(self)
        super().__init__(token_list)
        
    def apply_convention(self):
        cls = self.__class__
        if not cls.convention_applied:
            cls.convention_applied = True
            for name in cls.name_list:
                name.insert(0, self.module_name.capitalize()+'_')

st1_name = Name("my_struct")
st1 = C.Struct(st1_name, ["int member1=0"], auto_typedef=True)
var1 = C.Var("char* member2=43")
st1 += var1
st1 += "long member3"
st1.extend(["long member4", "size_t member5"])


print(repr(st1_name))
st1_name.extend("my_struct")
st1_name.insert(0, "blop_")
#st1_name[1] = "foo_bar"
print(repr(st1_name))


st1.name = Name(42)
#st1.name = C.TokenList(str(st1.name)+'gaga')
st1.name = Name(st1.name.inline_str()+'_gaga')

#st1.name.module_name = "jean bob"
st1.name.apply_convention()
st1.name.inline_str_filter = lambda x: core.format_string(x, 'UPPER_UNDERSCORE_CASE')

print(st1.name.module_name+' hoho')
print(Name.module_name+' hoho')

print(st1)
print(var1.type)
print(var1)
print(st1[2].type)
print(st1[4].type)


class Expr2(C.Expr):
    #pass
    def __init__(self, *args, **kwargs):
        self._Expr__format_string = 'Expression: {expr}'
        super().__init__(*args, **kwargs)

expr2 = Expr2('expression')
print(expr2.freestanding_str())