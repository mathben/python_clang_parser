#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import uuid

from ast_object import ASTObject
from location import Location
import util


class FakeStatement(object):
    def __init__(self, name, begin_stmt=None, location=None):
        self.name = name
        self.location = location
        self.begin_stmt = begin_stmt
        self.unique_name = uuid.uuid4()

    def label(self):
        return "%s\nline %s" % (self.name, self.location.line)


class Statement(ASTObject):
    def __init__(self, cursor, force_name=None, count_stmt=None, is_condition=False, method_obj=None,
                 stack_parent=None):
        super(Statement, self).__init__(cursor, filename=None, store_variable=False)
        if method_obj:
            # start the stack for stmt_child
            stack_parent = [self]

        if method_obj and not force_name:
            self.name = method_obj.name_tmpl
        else:
            self.name = Statement.get_stmt_name(cursor.kind) if not force_name else force_name
        self.is_unknown = self.name == "UNKNOWN"
        self.unique_name = uuid.uuid4()
        self.stmt_child = []
        self._is_condition = is_condition
        self.contain_else = False
        self.description = ""
        self.next_stmt = None
        self.end_stmt = None
        self.method_obj = method_obj
        self._fill_statement(cursor, count_stmt=count_stmt, stack_parent=stack_parent)
        if count_stmt is not None:
            count_stmt[self.name] += 1

        # exception for condition
        if is_condition:
            self.name = "condition"
        if cursor.kind in util.dct_alias_operator_stmt.keys():
            self._construct_description()

    def _construct_description(self):
        for child in self.stmt_child:
            self.description += "%s %s" % (child.type, child.name_tmpl)

    def label(self):
        desc = "" if not self.description else "\n%s" % self.description
        return "%s\nline %s%s" % (self.name, self.location.line, desc)

    def _fill_statement(self, cursor, count_stmt=None, stack_parent=None):
        if self.is_block_stmt() or self.method_obj:
            end_location = Location(cursor.extent.end)
            self.end_stmt = FakeStatement("end " + self.name, begin_stmt=self, location=end_location)

        if self.is_return():
            self.next_stmt = stack_parent[0].end_stmt

        if not self.method_obj:
            stack_parent.append(self)

        i = 0
        # child_lst_size = len(cursor.get_children())
        stmt = None
        lst_child = list(cursor.get_children())
        for child in lst_child:
            is_condition = not i and cursor.kind in util.dct_alias_condition_stmt.keys()
            stmt = Statement(child, count_stmt=count_stmt, is_condition=is_condition, stack_parent=stack_parent)
            self.stmt_child.append(stmt)

            i += 1
        # get the last stmt of child to point on his parent
        if stmt and not stmt.next_stmt and not stmt.is_unknown and stmt.kind not in util.dct_alias_compound_stmt.keys():
            stmt.next_stmt = stack_parent[-2].end_stmt

        stack_parent.pop()

    def is_operator(self):
        return self.kind in util.dct_alias_operator_stmt.keys()

    def is_common_stmt(self):
        return self.kind in util.dct_alias_common_stmt.keys()

    def is_block_stmt(self):
        return self.kind in util.dct_alias_block_stmt.keys()

    def is_return(self):
        return self.kind in util.dct_alias_return_stmt.keys()

    def __repr__(self):
        return "\"%s\"" % self.name

    @staticmethod
    def get_stmt_name(kind):
        stmt = util.dct_alias_stmt.get(kind)
        if not stmt:
            return "UNKNOWN"
        return stmt
