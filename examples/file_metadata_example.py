#! /usr/bin/env python3
# -*-coding:Utf-8 -*

import sys
import base64
import hashlib
import copy

# If BrownBat is not installed, this enable the example to be run from the root of the project or this directory
sys.path[0:0] = ['.', '..']

import brownbat.C as C
import brownbat.core as core

C.Node.config.enable_debug_comments = False

#print("#################")

header = C.HeaderFile("tmp/header_coucou", content_metadata=True)
header += C.Var("int hello=42")
#print(header)
#print(C.FileMetadata.extract_metadata(header).metadata)
#print(header.check_content(header))

#print("#################")

header2 = copy.deepcopy(header)
header2.append("hello world")
#print(header)
#print(header2)
#print(str(header.content_patch(header2.freestanding_str())))
#print(header.file_patch())
#print(header2.generated_file_has_changed())
#print(header2.user_has_changed_file())
header.write_file()
