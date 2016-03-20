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

    @staticmethod
    def label():
        return ""


class Statement(ASTObject):
    def __init__(self, cursor, force_name=None, count_stmt=None, is_condition=False, stack_parent=None):
        super(Statement, self).__init__(cursor, filename=None, store_variable=False)
        self.name = Statement.get_stmt_name(cursor.kind) if not force_name else force_name
        self.unique_name = uuid.uuid4()
        self.stmt_child = []
        self._is_condition = is_condition
        self.contain_else = False
        self.description = ""
        self.next_stmt = None
        self.end_stmt = None
        self._fill_statement(cursor, count_stmt=count_stmt)
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

    def _fill_statement(self, cursor, count_stmt=None):
        if self.is_block_stmt():
            end_location = Location(cursor.extent.end)
            self.end_stmt = FakeStatement("end " + self.name, begin_stmt=self, location=end_location)

        is_first_child = True
        for child in cursor.get_children():
            is_condition = is_first_child and cursor.kind in util.dct_alias_condition_stmt.keys()
            self.stmt_child.append(Statement(child, count_stmt=count_stmt, is_condition=is_condition))

            if is_first_child:
                is_first_child = False

    def is_operator(self):
        return self.kind in util.dct_alias_operator_stmt.keys()

    def is_condition(self):
        self._is_condition

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
