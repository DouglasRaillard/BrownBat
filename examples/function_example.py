#! /usr/bin/env python3
# -*-coding:Utf-8 -*

import sys

# If BrownBat is not installed, this enable the example to be run from the root of the project or this directory
sys.path[0:0] = ['.', '..']

import brownbat.C as C
import brownbat.core as core

my_function = C.Fun('my_fun')

local_var = C.Var('int my_local_var=42', parent=my_function)
index_var = C.Var('int i=0', parent=my_function)
for_loop = C.For(index_var.assign(0), (index_var,'<',local_var), (index_var,'++'), parent=my_function)
for_loop += 'printf("Hello World")'

print(my_function)
print(my_function.defi())