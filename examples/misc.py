#! /usr/bin/python3
# -*-coding:Utf-8 -*

import brownbat.C as C
import brownbat.core as core

class UserHeader():
    def __init__(self, path, system=False):
        self.path = path
        self.system = system
        self.include = C.PrepInclude(self.path, self.system)

    def include_in(self, code_file):
        if self.system:
            code_file.add_code(self.include, "system_includes")
        else:
            code_file.add_code(self.include, "other_includes")
