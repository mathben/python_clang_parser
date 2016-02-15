#!/usr/bin/env python2
# -*- coding: utf-8 -*-
import collections
import os
import sys

sys.path.append("/opt/llvm/tools/clang/bindings/python")
import clang.cindex

# clang.cindex.Config.set_library_path("/usr/lib/")
clang.cindex.Config.set_library_file("/opt/llvm/build/lib/libclang.so.3.7")


def get_tokens_statistic(cursor):
    # TODO to get else if, check if offset is inside of 5. c_child.location.offset
    lst_token_key = ["if", "else", "else if", "switch", "while", "for", "break", "continue", "return", "using"]
    lst_token = [c_child.spelling for c_child in cursor.get_tokens() if
                 c_child.kind is clang.cindex.TokenKind.KEYWORD and c_child.spelling in lst_token_key]
    return collections.Counter(lst_token)


def get_variables_statistic(cursor):
    lst_kind_var = [clang.cindex.CursorKind.VAR_DECL]
    return len([None for c_child in cursor.walk_preorder() if c_child.kind in lst_kind_var])


def get_annotations(cursor):
    return [c_child.displayname for c_child in cursor.get_children()
            if c_child.kind == clang.cindex.CursorKind.ANNOTATE_ATTR]


class ASTObject(object):
    def __init__(self, cursor, filename):
        self.name = cursor.spelling
        self.name_tmpl = cursor.displayname
        self.file_name = filename
        self.location_file_name = cursor.location.file.name
        self._kind_id = cursor.kind.value
        # self.annotations = get_annotations(cursor)
        self.mangled_name = cursor.mangled_name
        self.count_variable = get_variables_statistic(cursor)
        self.keywords = None

    @property
    def kind(self):
        return clang.cindex.CursorKind.from_id(self._kind_id)


class Class(ASTObject):
    def __init__(self, cursor, filename):
        super(Class, self).__init__(cursor, filename)

        self.methods = [Method(c_child, filename) for c_child in cursor.get_children() if
                        c_child.kind is clang.cindex.CursorKind.CXX_METHOD]

    def __repr__(self):
        return self.to_string()

    def to_string(self):
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


class Function(ASTObject):
    def __init__(self, cursor, filename):
        super(Function, self).__init__(cursor, filename)
        self.keywords = get_tokens_statistic(cursor) + collections.Counter(var=self.count_variable)

    def __repr__(self):
        return self.to_string()

    def to_string(self):
        # file_str = "File %s\n" % self.file_name
        if self.kind is clang.cindex.CursorKind.CXX_METHOD:
            function_str = "%s %s" % (self.name, self.keywords.items())
        else:
            function_str = "\t+--%s - %s %s" % (self.kind, self.name, self.keywords.items())
        # return file_str + function_str
        return function_str

    def merge(self, fct):
        if not isinstance(fct, Function):
            return
        self.count_variable += fct.count_variable
        self.keywords += fct.keywords


class Method(Function):
    def __repr__(self):
        return self.to_string()

    def to_string(self):
        return "%s %s" % (self.name, self.keywords.items())


def build_classes(cursor, filename, dir_name, is_first_call=True):
    result = []
    # ignore Cursor Kind
    all_kind = [clang.cindex.CursorKind.CLASS_DECL, clang.cindex.CursorKind.CLASS_TEMPLATE,
                clang.cindex.CursorKind.NAMESPACE, clang.cindex.CursorKind.FUNCTION_TEMPLATE,
                clang.cindex.CursorKind.FUNCTION_DECL, clang.cindex.CursorKind.CXX_METHOD]

    # not work with .hh and .cc in same time
    header_filename = filename[filename.rfind("/"):-3]
    children_cursor = [m for m in cursor.get_children() if m.location.file and dir_name in m.location.file.name and
                       header_filename in m.location.file.name and m.kind in all_kind]

    # TODO merge when method is not in class, but in namespace
    for c_child in children_cursor:
        if c_child.kind in [clang.cindex.CursorKind.CLASS_DECL, clang.cindex.CursorKind.CLASS_TEMPLATE]:
            cls = Class(c_child, filename)
            result.append(cls)
        elif c_child.kind == clang.cindex.CursorKind.NAMESPACE:
            result.extend(build_classes(c_child, filename, dir_name, is_first_call=False))
        elif c_child.kind in [clang.cindex.CursorKind.FUNCTION_TEMPLATE, clang.cindex.CursorKind.FUNCTION_DECL,
                              clang.cindex.CursorKind.CXX_METHOD]:
            fct = Function(c_child, filename)
            result.append(fct)

    # merge header with src
    if is_first_call:
        # merge with class first
        [cls.merge_method(result) for cls in result if isinstance(cls, Class)]
        # merge with other method
        result = merge_method(result)

    return result


def merge_method(lst_method):
    result = []
    for new_method in lst_method:
        if not isinstance(new_method, Function) and not isinstance(new_method, Method):
            result.append(new_method)
            continue

        if not new_method.mangled_name:
            result.append(new_method)
            continue

        for old_method in [m for m in result if isinstance(m, Function) or isinstance(m, Method)]:
            if new_method.mangled_name == old_method.mangled_name:
                old_method.merge(new_method)
                # no need to search a new brother
                break
        else:
            result.append(new_method)

    return result


def clang_parser(arg):
    _file_name = arg[0]
    _dir_name = arg[1]
    _clang_arg = arg[2]

    # index = clang.cindex.Index(clang.cindex.conf.lib.clang_createIndex(False, True))  # True to display diagnostic
    _index = clang.cindex.Index(clang.cindex.conf.lib.clang_createIndex(False, False))
    absolute_file_path = os.path.join(_dir_name, _file_name)
    _translation_unit = _index.parse(absolute_file_path, ['-x', 'c++', '-std=c++11'] + _clang_arg)
    _result = build_classes(_translation_unit.cursor, _file_name, _dir_name)
    return _file_name, _clang_arg, _result
