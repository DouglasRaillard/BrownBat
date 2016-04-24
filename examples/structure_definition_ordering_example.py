#! /usr/bin/env python3
# -*-coding:Utf-8 -*

import sys

# If BrownBat is not installed, this enable the example to be run from the root of the project or this directory
sys.path[0:0] = ['.', '..']

import brownbat.C as C
import brownbat.core as core
C.Node.config.enable_debug_comments = True


s1 = C.Struct('s1', ('s2 *a'))
s2 = C.Struct('s2', ('s3 *a'))
s3 = C.Struct('s3', ('s4 *a=3', 's5 *b'))
s4 = C.Struct('s4', ('s1 *a'))
s5 = C.Struct('s5', ('s3 *b'))

cont = C.OrderedTypeContainer()
cont.append('int aa = 42')
cont.append(s3)
cont.append(s3.designated_init())
cont.append(s1)
cont.append(s2)
cont.append(s4)
cont.append(s5)

desig_init = C.StructDesignatedInitializer({'a':3, 'b.c':4, 'b.d':'"hello world"', 'b.e.a':42, 'b.e.b':43})
desig_init.side_comment = 'hello my dear :D'
type_translation_map={
    str: C.Type('char', ''),
    int: 'int',
}

crafted_struct = desig_init.struct(name='my_struct2')
v2 = C.Var(name='crafted_var', type=crafted_struct, initializer=crafted_struct.designated_init())

cont.append(desig_init)

v1 = C.Var('int bb', initializer=desig_init)
cont.append(v1.decl())
cont.append(v1.extern_decl())

cont.append(v1.assign(desig_init))
print(desig_init['b.c'])


root_cont = C.HeaderFile('blop', node_list=[cont])
print(root_cont)
print(crafted_struct)
print(v2.decl())
print(desig_init)

print(C.Enum(name='my_enum', member_list=('A','B')).anonymous())

v2 = C.Var(name='my_array', type=C.Type('int'))
print(v2.decl())
