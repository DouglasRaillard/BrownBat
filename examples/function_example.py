#! /usr/bin/env python3
# -*-coding:Utf-8 -*

import sys

# If BrownBat is not installed, this enable the example to be run from the root of the project or this directory
sys.path[0:0] = ['.', '..']

import brownbat.C as C
import brownbat.core as core

C.Node.config.enable_debug_comments = True

my_function = C.Fun('my_fun')

local_var = C.Var('int my_local_var=42', parent=my_function)
index_var = C.Var('int i=0', parent=my_function)
for_loop = C.For(index_var.assign(0), (index_var,'<',local_var), (index_var,'++'), parent=my_function, comment='loop comment')
for_loop += 'printf("Hello World")'

print(my_function)
print(my_function.defi())


struct = C.Struct('my_struct', ('int a=1', 'int b=4'))
struct.append(C.Var('int c=42'))
f_def = struct[0].defi()
struct[0].type = 'long'
s_def = struct[0].defi()
print(f_def)
print(s_def)

print(struct.forward_decl())
print(struct)
struct2 = C.Struct('my_struct2', ('int a2=1', 'int b2=33'))
struct.append(C.Var(name='d', type=struct2, initializer=struct2.designated_init()))
var = C.Var(name='my_var', type=+struct, initializer=(+struct)**~struct.designated_init())
print(var>>'blop' == 42)
print(var.defi())
print(var.extern_decl())