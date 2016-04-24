#! /usr/bin/python3
# -*-coding:Utf-8 -*


import sys
# If BrownBat is not installed, this enable the example to be run from the root of the project or this directory
sys.path[0:0] = ['.', '..']


import brownbat.C as C
import brownbat.core as core

#C.Node.enable_debug_comments()

x_range = 2
y_range = 5


x1_var = C.Var("INT16U x1")
y1_var = C.Var("INT16U y1")

x2_var = C.Var("INT16U x2")
y2_var = C.Var("INT16U y2")


switch_level1 = C.Switch(x1_var)
for x1 in range(x_range):
    switch_level2 = C.Switch(y1_var)
    switch_level1[x1] = switch_level2

    for y1 in range(y_range):
        switch_level3 = C.Switch(x2_var)
        switch_level2[y1] = switch_level3

        for x2 in range(x_range):
            switch_level4 = C.Switch(y2_var)
            switch_level3[x2] = switch_level4

            for y2 in range(y_range):
                switch_level4[y2] = C.StmtContainer(comment="Load route from ("+str(x1)+","+str(y1)+") to ("+str(x2)+","+str(y2)+")")
                
                var1 = C.Var('int kkk', side_comment='Hello')
                expr1 = var1.assign(42)
                
                switch_level4[y2] += var1
                switch_level4[y2] += expr1
                

switch_level1['default'] = 'do 42'
print(switch_level1)

sw = C.Switch("hello")
sw['grok'] = 'Lost to the game'
sw['grok2'] = 'Lost to the game'
for value, code in sw.items():
    print(str(value)+' :  '+str(code).strip())
#print(sw)

