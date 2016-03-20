#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import uuid

from ast_object import ASTObject
from clang_parser import clang
from location import Location
import util


class FakeStatement(object):
    def __init__(self, name, begin_stmt=None, location=None, next_stmt=None):
        self.name = name
        self.location = location
        self.begin_stmt = begin_stmt
        self.unique_name = uuid.uuid4()
        self.next_stmt = next_stmt

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
        self.is_unknown = self.name == "UNKNOWN" and not is_condition
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
        if cursor.kind in util.dct_alias_operator_stmt:
            self._construct_description()

    def _construct_description(self):
        for child in self.stmt_child:
            self.description += "%s %s\n" % (child.type, child.name_tmpl)
        # remove end line
        self.description = self.description.strip("\n")

    def label(self):
        desc = "" if not self.description else "\n%s" % self.description
        return "%s\nline %s%s" % (self.name, self.location.line, desc)

    def _fill_statement(self, cursor, count_stmt=None, stack_parent=None):
        if self.is_block_stmt() or self.is_root():
            if stack_parent[-1].kind is clang.cindex.CursorKind.IF_STMT:
                # get end_stmt of his parent "if" for "else if" stmt
                self.end_stmt = stack_parent[-1].end_stmt
            else:
                # create new end_stmt
                end_location = Location(cursor.extent.end)
                next_stmt = self.get_last_stmt_from_stack(stack_parent, util.dct_alias_loop_stmt)
                self.end_stmt = FakeStatement("end " + self.name, begin_stmt=self, location=end_location,
                                              next_stmt=next_stmt)

        if self.is_stmt_return():
            # get function stmt
            self.next_stmt = stack_parent[0].end_stmt

        if self.is_stmt_break():
            # exit last block end stmt of switch or loop stmt
            last_stmt = self.get_last_stmt_from_stack(stack_parent, util.dct_alias_affected_break_stmt)
            if last_stmt:
                self.next_stmt = last_stmt.end_stmt

        if self.is_stmt_continue():
            # go to last block of switch or loop stmt
            self.next_stmt = self.get_last_stmt_from_stack(stack_parent, util.dct_alias_affected_break_stmt)

        if not self.is_root():
            # add stmt on stack, ignore if root, because already in stack
            stack_parent.append(self)

        stmt = None
        lst_child = list(cursor.get_children())
        for child in lst_child:
            # condition is first item of child and need to be a condition stmt
            is_condition = not stmt and cursor.kind in util.dct_alias_condition_stmt
            stmt = Statement(child, count_stmt=count_stmt, is_condition=is_condition, stack_parent=stack_parent)
            self.stmt_child.append(stmt)

        # get the last stmt of child to point on his parent
        if stmt and not stmt.next_stmt and not stmt.is_unknown \
                and stmt.kind not in util.dct_alias_compound_stmt \
                and stmt.kind in util.dct_alias_operator_stmt:
            stmt.next_stmt = stack_parent[-2].end_stmt

        stack_parent.pop()

    def is_operator(self):
        return self.kind in util.dct_alias_operator_stmt

    def is_common_stmt(self):
        return self.kind in util.dct_alias_common_stmt

    def is_block_stmt(self):
        return self.kind in util.dct_alias_block_stmt

    def is_stmt_return(self):
        return self.kind in util.dct_alias_return_stmt

    def is_stmt_break(self):
        return self.kind in util.dct_alias_break_stmt

    def is_stmt_continue(self):
        return self.kind in util.dct_alias_continue_stmt

    def is_root(self):
        return bool(self.method_obj)

    def __repr__(self):
        return "\"%s\"" % self.name

    @staticmethod
    def get_stmt_name(kind):
        stmt = util.dct_alias_stmt.get(kind)
        if not stmt:
            return "UNKNOWN"
        return stmt

    @staticmethod
    def get_last_stmt_from_stack(stack, dct_alias_stmt):
        # return None if not found
        for stmt in reversed(stack):
            if stmt.kind in dct_alias_stmt:
                return stmt
