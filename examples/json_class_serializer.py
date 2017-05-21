#! /usr/bin/env python3
# -*-coding:Utf-8 -*

import sys
import json

# If BrownBat is not installed, this enable the example to be run from the root of the project or this directory
sys.path[0:0] = ['.', '..']

import brownbat.C as C
import brownbat.core as core

C.Node.config.enable_debug_comments = False


public_access_specifier = C.TokenList("public:")
private_access_specifier = C.TokenList("private:")

with open("class.json", "r") as f:
    classes_dict = json.loads(f.read())
    for class_name, class_desc in classes_dict.items():
        class_body = C.BlockStmt()

        constructor = C.Fun(name=class_name, return_type='')
        serialize_fun = C.Fun(
            name = class_name+'::serialize',
            param_list = (
                C.Var("char *string").decl(),
                C.Var("size_t length").decl(),
            )

        )
        printf_token_list = []
        printf_param_list = []

        deserialize_fun = C.Fun(
            name=class_name+'::deserialize',
            return_type = class_name,
            param_list = [C.Var("const char *string").decl()]
        )

        # Public attributes
        class_body += public_access_specifier
        class_body += constructor
        class_body += serialize_fun
        class_body += deserialize_fun

        for attr, value in class_desc["public"].items():
            attr_obj = C.Var(attr, initializer=value)
            # Build a StructMember to avoid having the initial value
            # in member declaration
            class_body += C.StructMember(attr_obj)
            constructor.param_list += attr_obj.decl()
            constructor += attr_obj.assign(attr_obj)

            attr_name = str(attr_obj.name).strip()
            attr_type = str(attr_obj.type).strip()

            # Handle attribute depending on their type
            if attr_type == 'int':
                printf_token = '\\"'+attr_name+'\\": '+'%i'
                printf_param = C.TokenList(('this->',attr_name))
            else:
                printf_token = '\\"'+attr_name+'\\": '+'\\"%s\\"'
                printf_param = C.TokenList(('this->',attr_name,'.string()'))

            printf_param_list.append(printf_param)
            printf_token_list.append(printf_token)
            print(printf_token_list)

        # Private attributes
        class_body += private_access_specifier
        for attribute in class_desc["private"]:
            class_body += C.StructMember(attribute)

        printf_string = '"{'+", ".join(printf_token_list)+'}"'
        printf_param_string = ', '.join(str(param) for param in printf_param_list)

        serialize_fun += C.Expr(('snprintf(string, length, ',printf_string,', ',printf_param_string,')'))


        print("class "+class_name)
        print(class_body)

