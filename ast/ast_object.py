#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from clang_parser import clang
from location import Location


class ASTObject(object):
    def __init__(self, cursor, filename=None, store_variable=True):
        super(ASTObject, self).__init__()
        # cursor information
        self.name = cursor.spelling
        self.spelling = cursor.spelling
        self.name_tmpl = cursor.displayname
        self.location = Location(cursor.location)
        self._kind_id = cursor.kind.value
        self.mangled_name = cursor.mangled_name
        self._access_specifier = cursor.access_specifier.value
        self.type = cursor.type.spelling
        self._kind_type_id = cursor.type.kind.value

        self.file_name = filename if filename else self.location.file.name
        self.variable = ASTObject.get_variables(cursor) if store_variable else []
        self.count_variable = len(self.variable)
        self.keywords = None

    @property
    def kind(self):
        return clang.cindex.CursorKind.from_id(self._kind_id)

    @property
    def type_kind(self):
        return clang.cindex.TypeKind.from_id(self._kind_type_id)

    @property
    def access_specifier(self):
        return clang.cindex.AccessSpecifier.from_id(self._access_specifier)

    @staticmethod
    def _get_dot_format(ast_obj, parent_ast_obj=None):
        # example : "+ name : string"
        #
        # + Public
        # - Private
        # # Protected
        # ~ Package (default visibility)

        if ast_obj.access_specifier == clang.cindex.AccessSpecifier.PUBLIC:
            sign = "+ "
        elif ast_obj.access_specifier == clang.cindex.AccessSpecifier.PROTECTED:
            sign = "# "
        elif ast_obj.access_specifier == clang.cindex.AccessSpecifier.PRIVATE:
            sign = "- "
        elif ast_obj.access_specifier == clang.cindex.AccessSpecifier.NONE:
            sign = "~ "
        else:  # elif cursor.access_specifier == clang.cindex.AccessSpecifier.INVALID:
            print("Warning, receive AccessSpecifier.Invalid for %s obj, from : %s. File %s, mangled %s" % (
                ast_obj.name_tmpl, parent_ast_obj.name_tmpl if parent_ast_obj else None, ast_obj.file_name,
                ast_obj.mangled_name))
            sign = "? "

        return "%s %s : %s" % (sign, ast_obj.name_tmpl, ast_obj.type)

    @staticmethod
    def get_variables(cursor):
        # lst_supported_type = []
        lst_blacklist_type_kind = [
            clang.cindex.TypeKind.CONSTANTARRAY  # this is struct type
        ]
        lst_kind_var = [clang.cindex.CursorKind.VAR_DECL, clang.cindex.CursorKind.FIELD_DECL]
        return [Variable(c, c.location.file.name, store_variable=False) for c in
                cursor.walk_preorder() if c.kind in lst_kind_var and c.type.kind not in lst_blacklist_type_kind]


class Variable(ASTObject):
    def __init__(self, cursor, filename=None, store_variable=True):
        super(Variable, self).__init__(cursor, filename=filename, store_variable=store_variable)
