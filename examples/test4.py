#! /usr/bin/python3
# -*-coding:Utf-8 -*


import collections
import copy
import sys
# If BrownBat is not installed, this enable the example to be run from the root of the project or this directory
sys.path[0:0] = ['.', '..']

import brownbat.C as C
import brownbat.core as core


#C.Node.config.enable_debug_comments = True

class FunName:
    def __init__(self, name):
        self.name = name
        
    def __str__(self):
        return str(self.name)

fun1_name = FunName('my_func')
fun1 = C.Fun(fun1_name, "void", 'static', ['int param1=3', 'double param2'], side_comment='fun1 side comment')
if1 = C.If('Hello')
fun1 += if1
def create_while():
    return C.While('Blop', comment='my comment')
while1 = create_while()
while1.side_comment = 'blop 42'
if1 += while1
#if1 += C.Expr('Inside hello')+C.If('HelloIf')
#if1 += C.Stmt("""
if1 += C.IndentedTokenList(
"""
for Blip; do
    World
done""")

else1 = C.Else()
fun1 += else1
fun1bis = copy.copy(fun1)
fun1bis.insert(0, 'echo')
print(fun1.defi())
print(fun1bis.defi().freestanding_str())
print(hasattr(fun1.defi(), 'decl'))
fun1_call = fun1(42)
fun1copy = copy.deepcopy(fun1)
#fun1_call.side_comment = C.SingleLineCom('call comment')
#fun1_call.side_comment = 'my comment from file: '+str(frame[1])+' line: '+str(frame[2])
#fun1_call.side_comment = 'Current position is '+C.CurrentLine()

print(fun1_call)

cont1 = C.StmtContainer()
var1 = C.Var(
    'volatile static  union {f k; i j}   *   aa_echo [ 99   ]=42',
    storage_list="static blop volatile",
    comment='this is var comment',
    side_comment='this is var side comment',
    #type="long",
    parent = cont1    
)
var1.name.inline_str_filter = lambda x: core.format_string(x, 'lowerCamelCase')
var1 += '_aa_hello_bb'
var1_def = var1.defi()
var1.side_comment = 'my side comment'
#var1_def.side_comment = 'my def side comment'
#var1_def.comment = 'my def comment'

print(C.StmtContainer( var1_def))
print(var1.cast('int'))
exit(42)
#cont1.append(var1)

expr1 = C.Expr('coucou')

expr2 = expr1+var1
var2 = var1+expr2
#var2 = copy.copy(var1)
var2.insert(0, expr2)
var2.array_size = C.TokenList(int(var2.array_size[0])*3)
#print(type(var2.array_size[0]))

cont1bis = C.StmtContainer(parent=cont1)
#cont1.append(cont1bis)
#cont1 += cont1bis
cont1bis += 'cont1bis expr'

print(cont1)
#print(expr2.token_list)
print("###############")
print(expr2)
print(var2.defi().freestanding_str(' '))


prepif1 = C.PrepIf('MACRO', indent_content=False)
cont2 = C.StmtContainer(parent=prepif1)
cont2 += 'cont2 inside'
prepif1 += 'hello'
prepif1 += cont2

if2 = C.If('my_cond 2', parent=cont2)
if1 = C.If('my_cond', side_comment=C.TokenList((C.NewLine(),C.Com('hellow long very very long string'))), parent=cont2)
if3 = C.If('my_cond 3', parent=if2)
print(prepif1)
print(C.Backtrace().freestanding_str())