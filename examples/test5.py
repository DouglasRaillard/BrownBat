#! /usr/bin/python3
# -*-coding:Utf-8 -*


import collections
import copy

import sys
# If BrownBat is not installed, this enable the example to be run from the root of the project or this directory
sys.path[0:0] = ['.', '..']

import brownbat.C as C
import brownbat.core as core

v=C.Var('int aa=33')
nc=C.NodeContainer()
nc.adopt_node(v)
print(repr(str(nc)))