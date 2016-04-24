#! /usr/bin/python3
# -*-coding:Utf-8 -*


import traceback
import collections

import sys
# If BrownBat is not installed, this enable the example to be run from the root of the project or this directory
sys.path[0:0] = ['.', '..']


import brownbat.C as C
import brownbat.core as core

C.Node.config.enable_debug_comments = True


expr1 = C.Var("int aa=33", storage_list='static')
print(type(expr1))
expr1 *= 3
print(type(expr1))
#~ print(expr1)
#~ print("".join(str(token) for token in expr1.token_list))
print(C.Expr.__str__(expr1))
print(expr1.freestanding_str())
print(expr1.decl())
expr1bis = C.Var(name="bb", type='int', array_size=3, storage_list='static')
print(expr1bis.decl())
print(expr1bis.array_size)


print("ho")
expr2 = C.Expr(expr1)
expr2 *= 3
print(expr2.inline_str())
print(expr2.freestanding_str())
print('===========')
#fun1 = C.Fun("my_function", "void", 'static', ['int param1=3', 'double param2'])
fun1 = C.Fun("my_function", "void", '', ['int param1=3', 'double param2'])
else_fun1 = C.If()
fun1 += else_fun1
else_fun1 += C.Else()
fun1 += C.Expr('Inside hello')+C.If('HelloIf')
#else_fun1 += C.Stmt("""
else_fun1 += C.IndentedTokenList("""
for Blip; do
    World
done
""")
fun1.extend([expr1.decl(),'print a var'])
fun1 *= 2
fun1 += C.NewLine()
fun1 += "this is 42"
print(fun1)
print("-------------------")
#print(fun1.inline_str())
print(fun1.freestanding_str())
print(fun1.decl())
print(fun1(43, 33).inline_str())
print("-------------------")

enum1 = C.Enum('myEnum', ['A', 'B'])
print(enum1)
print(enum1.freestanding_str())

print(C.Expr(enum1))
enum1 += 'C'
enum1.extend((C.Var('int D[44]=57'), C.TokenList('E')))
enum1.extend('int F=3')
enum1[2].comment = C.Com('Hi im a comment :)')
print("##############")
print(enum1.freestanding_str())
print("##############")
var1 = C.Var(name="blop", initializer=53, type=enum1)
print(var1)
print(var1.assign(enum1[-1]))

var4 = C.Var("float cchellow=33")
print(var4)
expr4 = C.Expr((var4, ' == ', '42'))
print(expr4)
print(C.TokenList(("hello", "world")))

