#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from clang_parser import clang
from ast_object import ASTObject
from function import Method
from function import Function


class Class(ASTObject):
    def __init__(self, cursor, filename=None):
        super(Class, self).__init__(cursor, filename=filename)

        self.methods = [Method(c_child, filename) for c_child in cursor.get_children() if
                        c_child.kind is clang.cindex.CursorKind.CXX_METHOD]

        self.derived_class = [Class(c_child) for c_child in cursor.get_children() if
                              c_child.kind is clang.cindex.CursorKind.CXX_BASE_SPECIFIER]

        self.namespace_name = cursor.type.spelling

    def __repr__(self):
        return self.to_string()

    def get_dot(self):
        # example : "{Animal|+ name : string\l+ age : int\l|+ die() : void\l}"
        # if self.derived_class:
        #     self.namespace_name += " - " + str(self.derived_class)
        msg = "{%s|%s|%s}" % (self.namespace_name,
                              Class._get_dot_lst_cursor(self.variable, self),
                              Class._get_dot_lst_cursor(self.methods, self))
        # need to remove bad character
        msg = msg.replace("<", "\\<")
        msg = msg.replace(">", "\\>")
        return msg

    # dot function
    @staticmethod
    def _get_dot_lst_cursor(lst_ast_obj, parent_ast_obj):
        char_new_line = "\\l"
        # example : "+ name : string\l+ age : int\l"
        # or empty : ""
        str_var = char_new_line.join([ASTObject._get_dot_format(var, parent_ast_obj) for var in lst_ast_obj])
        if str_var:
            str_var += char_new_line
        return str_var

    def to_string(self):
        # TODO change this to_string. Move this into export.
        # file_str = "File %s\n" % self.file_name
        class_str = "\t+--%s - %s\n" % (self.kind, self.name_tmpl)
        method_str = "\n".join(["\t|\t+--%s - %s" % (clang.cindex.CursorKind.CXX_METHOD, f) for f in self.methods])
        # return file_str + class_str + method_str
        return class_str + method_str

    def merge_method(self, lst_method):
        i = len(lst_method)
        for method in reversed(lst_method):
            i -= 1
            if not isinstance(method, Function) and not isinstance(method, Method):
                continue
            j = 0
            for class_method in self.methods:
                if method.mangled_name == class_method.mangled_name:
                    self.methods[j] = method
                    del lst_method[i]
                j += 1
