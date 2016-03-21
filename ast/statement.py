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

    @staticmethod
    def is_compound():
        return False


class Statement(ASTObject):
    def __init__(self, cursor, force_name=None, count_stmt=None, is_condition=False, method_obj=None,
                 stack_parent=None, before_stmt=None):
        super(Statement, self).__init__(cursor, filename=None, store_variable=False)
        if method_obj:
            # start the stack for stmt_child
            stack_parent = [self]

        if method_obj and not force_name:
            self.name = method_obj.name_tmpl
        else:
            self.name = self.get_stmt_name(cursor.kind) if not force_name else force_name
        self.is_unknown = self.name == "UNKNOWN" and not is_condition
        self.unique_name = uuid.uuid4()
        self.stmt_child = []
        self._is_condition = is_condition
        self.stmt_condition = None
        self.contain_else = False
        self.description = ""
        self.before_stmt = before_stmt
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

    def info(self):
        def generic_info(stmt, key):
            msg = ""
            if stmt:
                msg += " - (%s " % key
                if type(stmt) is dict:
                    for key, value in stmt.items():
                        msg += "[\"%s\" line %s \"%s\"] " % (key, value.location.line, value.name)
                    msg = msg.rstrip() + ")"
                else:
                    msg += "[line %s \"%s\"])" % (stmt.location.line, stmt.name)
            return msg

        return generic_info(self.before_stmt, "from") + generic_info(self.next_stmt, "to")

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
        elif self.is_stmt_break():
            # exit last block end stmt of switch or loop stmt
            last_stmt = self.get_last_stmt_from_stack(stack_parent, util.dct_alias_affected_break_stmt)
            if last_stmt:
                self.next_stmt = last_stmt.end_stmt
        elif self.is_stmt_continue():
            # go to last block of switch or loop stmt
            last_stmt = self.get_last_stmt_from_stack(stack_parent, util.dct_alias_affected_break_stmt)
            self.next_stmt = last_stmt.stmt_condition

        if not self.is_root():
            # add stmt on stack, ignore if root, because already in stack
            stack_parent.append(self)

        before_stmt = self
        stmt = None
        lst_child = list(cursor.get_children())
        # keep trace on stmt condition to build next_stmt when child is instance
        lst_condition_child = []
        for child in lst_child:
            # condition is first item of child and need to be a condition stmt
            is_condition = not stmt and cursor.kind in util.dct_alias_condition_stmt
            if before_stmt.is_compound():
                good_before_stmt = before_stmt.before_stmt
            else:
                good_before_stmt = before_stmt

            stmt = Statement(child, count_stmt=count_stmt, is_condition=is_condition, stack_parent=stack_parent,
                             before_stmt=good_before_stmt)
            self.stmt_child.append(stmt)

            if not before_stmt.next_stmt and not stmt.is_unknown:
                if before_stmt.is_compound():
                    before_stmt.before_stmt.next_stmt = stmt
                else:
                    before_stmt.next_stmt = stmt

            before_stmt = stmt.end_stmt if stmt.end_stmt else stmt

            if is_condition:
                if not self.stmt_condition:
                    self.stmt_condition = stmt
                lst_condition_child.append(stmt)

        if lst_condition_child:
            # TODO what we do we many condition? else?
            if len(lst_condition_child) > 1:
                print("ERROR, find many condition child and only take first.")
            first_child = self.get_first_stmt_child(self.stmt_child)
            self.stmt_condition.next_stmt = {"False": self.end_stmt, "True": first_child}

        # get the last stmt of block (child) to point on his parent end_stmt
        if stmt and not stmt.next_stmt and not stmt.is_unknown \
                and not stmt.is_compound() \
                and stmt.is_operator():
            # don't point to a compound stmt, get last block stmt
            stmt.next_stmt = self.get_last_stmt_from_stack(stack_parent, util.dct_alias_block_stmt).end_stmt

        stack_parent.pop()
        # all node need a next_stmt and from_stmt

    def is_operator(self):
        return self.kind in util.dct_alias_operator_stmt

    def is_compound(self):
        return self.kind in util.dct_alias_compound_stmt and not self.is_root()

    def is_condition(self):
        return self._is_condition

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
        return "'%s' l %s" % (self.name, self.location.line)

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

    @staticmethod
    def get_first_stmt_child(lst_stmt_child):
        # return None if not found
        for stmt in lst_stmt_child:
            if stmt.kind in util.dct_alias_compound_stmt:
                return Statement.get_first_stmt_child(stmt.stmt_child)
            if not stmt.is_condition():
                return stmt
