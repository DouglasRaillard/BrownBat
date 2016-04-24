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

class Blop(C.StmtContainer):
    pass
    #Debug
    def __str__(self):
        string = super().__str__()
        #~ traceback.print_stack()
        return string

else_stmt = C.DoWhile('a buggy condition')
else_stmt2 = C.Else()
else_stmt2 += else_stmt

stmt = Blop()
else_stmt += stmt

stmt += "mmmm"
#~ print(list(stmt))

#~ print(C.Var("blop = 3"))

struct = C.Struct("ma_struct")
struct.name = 'ma_struct'
struct.name.str_filter = lambda x: core.format_string(x, 'UPPER_UNDERSCORE_CASE')
struct.name += '_name_end'
print(struct.name.inline_str())
t1 = struct
struct += "kk1"
struct += "kk2"
struct.extend(["int kk3", "kk4", "kk5"])
struct.append(C.Var(type='long', name='kk_long', initializer=53))
struct += C.Var('int kk6=44')
t2 = struct
t2[0] *= 3 # *= 3
print('#########################')
print(isinstance(t2[0], C.TokenList))
print(t1 is t2)
expr1 = C.Var("int aa=33")
expr1 *= 3
#~ print("".join(str(token) for token in expr1.token_list))
print(expr1)
print('#########################')
#~ struct.pop()


struct.append("aa")
print("================")
print(struct[-1].inline_str())
print("================")

else_stmt += struct
com1 = C.Com("This is a really long and boring comment that could be break up in multiple sentences but I did not see why I would do this because", auto_wrap=True)
#com1 = C.Com("hello world", auto_wrap=True)
else_stmt += com1
#com1 *= 30
#com1.insert(0, C.NewLine())

print(else_stmt2)
print()
var_i = C.Var(name='jean_jacques', type=struct, initializer=42)
#for_loop = C.For(var_i, (var_i,'<4'), var_i.assign((var_i,'+','1')), 'do some stuff')
for_loop = C.For('hello init', (var_i,'<4'), var_i.assign((var_i,'+','1')), 'do some stuff')
print(for_loop.freestanding_str())

enum1 = C.Enum('my_enum', ('aa=33'))
enum1.comment = C.Com("Enumeration comment")
node_container = C.StmtContainer()
node_container.append(enum1)
print(node_container)


def strip_nl(snippet):
    current_line_start_pos = 0
    last_line_start_pos = 0 # init value does not mean anything
    for position, char in enumerate(snippet):
        if char=='\n':
            last_line_start_pos = current_line_start_pos
            current_line_start_pos = position+1
        # Ignore white spaces, stop when something new shows up
        elif char!='\t' and char!=' ' and char!='\v':
            break
        
    # Remove beginning with spurious empty lines    
    snippet = snippet[last_line_start_pos:]
    return snippet

def strip_nl_2(snippet):
    line_list = snippet.split('\n')
    for i,line in enumerate(line_list):
        if not line.strip():
            continue
        else:
            snippet = '\n'.join(line_list[i:])
            break
        
    return snippet

string = '\t\n\t\n\n\nhello'
print('##########')
print(strip_nl(string))
print('##########')
print('##########')
print(strip_nl_2(string))
print('##########')