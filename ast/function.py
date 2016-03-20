#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import collections
import copy

from clang_parser import clang
from ast_object import ASTObject
from statement import Statement
import util


class Function(ASTObject):
    def __init__(self, cursor, filename=None):
        # TODO keep a link to his parent
        super(Function, self).__init__(cursor, filename)
        self.keywords_stmt = Function.get_tokens_statistic(cursor)
        self.keywords = self.keywords_stmt + collections.Counter(var=self.count_variable)
        # self.is_valid_cfg = False
        self.is_valid_cfg = True
        self.enable_cfg = False
        self.lst_cfg = collections.Counter()
        if filename in cursor.location.file.name:  # and not cursor.is_virtual_method():
            self.cfg = self._find_control_flow(cursor)
            is_type_void = cursor.result_type.kind is clang.cindex.TypeKind.VOID
            self.print_control_flow(self.cfg, is_type_void=is_type_void)
            # TODO add validation stmt, need to identify else stmt
            # self.validate_stmt()
            print("\n")
            self.enable_cfg = True
        else:
            self.cfg = []

    def get_dot(self):
        return ASTObject._get_dot_format(self)

    def __repr__(self):
        return self.to_string()

    @staticmethod
    def get_tokens_statistic(cursor):
        # TODO to get else if, check if offset is inside of 5. c_child.location.offset
        lst_token_key = ["if", "else", "else if", "switch", "case", "while", "for", "break", "continue", "return",
                         "using",
                         "try", "catch"]
        lst_token = [c_child.spelling for c_child in cursor.get_tokens() if
                     c_child.kind is clang.cindex.TokenKind.KEYWORD and c_child.spelling in lst_token_key]
        return collections.Counter(lst_token)

    @staticmethod
    def has_return(lst_cursor):
        for c in lst_cursor:
            if c.kind is clang.cindex.CursorKind.RETURN_STMT:
                return True
            if Function.has_return(c.stmt_child):
                return True
        return False

    def to_string(self):
        # file_str = "File %s\n" % self.file_name
        if self.kind is clang.cindex.CursorKind.CXX_METHOD:
            function_str = "%s %s" % (self.name, self.keywords.items())
        else:
            function_str = "\t+--%s - %s %s" % (self.kind, self.name, self.keywords.items())
        # return file_str + function_str
        return function_str

    def _find_control_flow(self, cursor):
        if not isinstance(cursor, clang.cindex.Cursor):
            return []

        # find first compound of function and get child control flow
        start_stmt_cursor = [c for c in cursor.get_children() if c.kind in util.dct_alias_compound_stmt]
        if len(start_stmt_cursor) != 1:
            print("Error, cannot find stmt child into function %s" % self)
            return None
        return Statement(start_stmt_cursor[0], count_stmt=self.lst_cfg, method_obj=self)

    def merge(self, fct):
        if not isinstance(fct, Function):
            return
        self.count_variable += fct.count_variable
        self.keywords += fct.keywords

    def print_control_flow(self, cfg, is_type_void=False):
        print("file %s line %s mangled %s" % (self.location.file.name, self.location.line, self.mangled_name))

        def print_cfg_child(stmt, level=0, no_iter=0):
            next_msg = "" if not stmt.next_stmt else " - go line %s" % stmt.next_stmt.location.line
            print("%s%s. %s - line %s%s" % (level * "\t", no_iter, stmt.name, stmt.location.line, next_msg))
            child_iter = 0
            for child in stmt.stmt_child:
                if not child.is_unknown:
                    print_cfg_child(child, level=level + 1, no_iter=child_iter)
                    child_iter += 1

            if stmt.end_stmt:
                end_stmt = stmt.end_stmt
                print("%s%s. %s - line %s" % (level * "\t", no_iter, end_stmt.name, end_stmt.location.line))

        print_cfg_child(cfg)

        if not is_type_void and not Function.has_return(cfg.stmt_child):
            print("Error, missing return statement.")

    def validate_stmt(self):
        if not self.keywords_stmt:
            return
        # ignore unknown
        lst_cfg = copy.copy(self.lst_cfg)
        del lst_cfg["UNKNOWN"]

        if lst_cfg != self.keywords_stmt:
            print("ERROR, Count stmt keyword '%s' is different of cfg '%s'." % (self.keywords_stmt, lst_cfg))
        else:
            self.is_valid_cfg = True
            print("INFO, %s" % self.keywords_stmt)


class Method(Function):
    def __repr__(self):
        return self.to_string()

    def to_string(self):
        return "%s %s" % (self.name, self.keywords.items())
