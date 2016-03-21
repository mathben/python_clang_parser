#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import uuid

from ast_object import ASTObject
from clang_parser import clang
from location import Location
import util


class ParentStatement(object):
    def __init__(self, *args, **kwargs):
        super(ParentStatement, self).__init__()
        self.description = ""
        self.before_stmt = {}
        self.next_stmt = {}
        self.begin_stmt = None
        self.end_stmt = None
        self._is_condition = False
        self.method_obj = None
        self.name = ""
        self.location = Location(None)
        self.result_has_from_recursive = None

    def is_end(self):
        return not self.end_stmt

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

    def is_loop_stmt(self):
        return self.kind in util.dct_alias_loop_stmt

    def is_stmt_return(self):
        return self.kind in util.dct_alias_return_stmt

    def is_stmt_break(self):
        return self.kind in util.dct_alias_break_stmt

    def is_stmt_continue(self):
        return self.kind in util.dct_alias_continue_stmt

    def is_root(self):
        return bool(self.method_obj)

    def label(self):
        desc = "" if not self.description else "\n%s" % self.description
        return "%s\nline %s%s" % (self.name, self.location.line, desc)

    def has_from_recursive(self, stmt=None):
        # TODO need to clean here
        # always pass None to stmt
        # return true if find root before stmt, else return false
        if not self.before_stmt and not self.is_root():
            return False

        if self.result_has_from_recursive is not None:
            # already check the recursion of this stmt
            return self.result_has_from_recursive

        if isinstance(stmt, ParentStatement) and stmt.result_has_from_recursive is not None:
            return stmt.result_has_from_recursive

        if stmt is None:
            self.result_has_from_recursive = result = self.has_from_recursive(self)
            return result

        if isinstance(stmt, dict):
            result = False
            # accumulate result, return true if find at least one true
            for obj_stmt in [obj for lst_stmt in stmt.values() for obj in lst_stmt]:
                # TODO create table to verify infinite loop
                result |= self.has_from_recursive(obj_stmt)
                if result:
                    return result

        if stmt.is_root():
            return True

        if stmt.before_stmt:
            return self.has_from_recursive(stmt.before_stmt)

        return False

    def info(self):
        def generic_info(stmt, key):
            if not stmt:
                return ""

            def get_msg_stmt(stmt_obj, s_key=None):
                lst_msg = []
                if isinstance(stmt_obj, dict):
                    for item_key, item_value in stmt_obj.items():
                        lst_msg.extend(get_msg_stmt(item_value, s_key=item_key))
                elif isinstance(stmt_obj, list):
                    for value in stmt_obj:
                        if not isinstance(value, ParentStatement):
                            continue
                        lst_msg.extend(get_msg_stmt(value, s_key=s_key))
                elif isinstance(stmt_obj, ParentStatement):
                    prefix = "\"%s\" " % s_key if s_key else ""
                    lst_msg.append("%sline %s \"%s\"" % (prefix, stmt_obj.location.line, stmt_obj.name))
                return lst_msg

            msg_stmt = "] [".join(get_msg_stmt(stmt))
            return " - (%s [%s])" % (key, msg_stmt) if msg_stmt else ""

        return generic_info(self.before_stmt, "from") + generic_info(self.next_stmt, "to")

    @staticmethod
    def get_first_end_before_stmt(stmt, stack_parent):
        if stmt.end_stmt:
            return stmt.end_stmt
        return ParentStatement.get_last_stmt_from_stack(stack_parent, util.dct_alias_block_stmt).end_stmt

    @staticmethod
    def get_first_before_stmt(stmt):
        for item in stmt.before_stmt.values():
            return item[0]
        return None

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
                return ParentStatement.get_first_stmt_child(stmt.stmt_child)
            if not stmt.is_condition():
                return stmt

    @staticmethod
    def _append_stmt(dct_stmt, _stmt, condition=None):
        if not (isinstance(_stmt, ParentStatement) and isinstance(dct_stmt, dict)):
            return
        if not dct_stmt or condition not in dct_stmt:
            dct_stmt[condition] = [_stmt]
        else:
            dct_stmt[condition].append(_stmt)

    @staticmethod
    def _add_stmt(before_stmt, next_stmt, condition=None):
        if isinstance(next_stmt, ParentStatement) and isinstance(before_stmt, ParentStatement):
            if before_stmt == next_stmt and before_stmt.is_end():
                # remove strange redondance, when end stmt point to itself
                return
            if not (before_stmt.is_condition() and next_stmt.is_compound()):
                ParentStatement._append_stmt(before_stmt.next_stmt, next_stmt, condition=condition)
            ParentStatement._append_stmt(next_stmt.before_stmt, before_stmt, condition=condition)

    def add_before_stmt(self, stmt, stack_parent):
        # stmt can be dict(key, Statement) or Statement or list(Statement)
        if self.is_unknown or not stmt or stmt.is_unknown:
            return

        if stmt.is_compound():
            # compound has always 1 before_stmt
            b_stmt = self.get_first_before_stmt(stmt)
            b_condition = None
            if b_stmt.is_condition():
                # if self.is_end():
                #     return
                # set condition branch
                if "True" not in b_stmt.next_stmt:
                    b_condition = "True"
                else:
                    b_condition = "False"
            self._add_stmt(b_stmt, self, condition=b_condition)

        elif stmt.is_stmt_return():
            self._add_stmt(stmt, stack_parent[0].end_stmt)

        elif stmt.is_stmt_break():
            last_loop_stmt = self.get_last_stmt_from_stack(stack_parent, util.dct_alias_affected_break_stmt)
            self._add_stmt(stmt, last_loop_stmt.end_stmt)

        elif stmt.is_stmt_continue():
            last_loop_stmt = self.get_last_stmt_from_stack(stack_parent, util.dct_alias_affected_break_stmt)
            self._add_stmt(stmt, last_loop_stmt.stmt_condition)

        elif self.is_loop_stmt() and self.is_end():
            self._add_stmt(stmt, self.begin_stmt.stmt_condition)

        else:
            b_condition = None
            if stmt.is_condition():
                # set condition branch
                if "True" not in stmt.next_stmt:
                    b_condition = "True"
                else:
                    b_condition = "False"
            self._add_stmt(stmt, self, condition=b_condition)

        # if self.is_stmt_return():
        #     self._add_stmt(self, stack_parent[0].end_stmt)

        # elif self.is_stmt_break():
        #     last_loop_stmt = self.get_last_stmt_from_stack(stack_parent, util.dct_alias_affected_break_stmt)
        #     self._add_stmt(stmt, last_loop_stmt.end_stmt)
        #
        # elif self.is_stmt_continue():
        #     last_loop_stmt = self.get_last_stmt_from_stack(stack_parent, util.dct_alias_affected_break_stmt)
        #     self._add_stmt(stmt, last_loop_stmt.stmt_condition)

    def __repr__(self):
        return "'%s' l %s" % (self.name, self.location.line)


class FakeStatement(ParentStatement):
    """
    A FakeStatement doesn't contain a clang obj
    """

    def __init__(self, name, begin_stmt=None, location=None):
        super(FakeStatement, self).__init__()
        self.name = name
        self.location = location
        self.begin_stmt = begin_stmt
        self.unique_name = uuid.uuid4()
        self.kind = begin_stmt.kind
        self.is_unknown = False

    def label(self):
        return "%s\nline %s" % (self.name, self.location.line)

    def is_root(self):
        return self.begin_stmt.is_root()


class Statement(ASTObject, ParentStatement):
    def __init__(self, cursor, force_name=None, count_stmt=None, is_condition=False, method_obj=None,
                 stack_parent=None, before_stmt=None):
        super(Statement, self).__init__(cursor, filename=None, store_variable=False)

        if force_name:
            self.name = force_name
        elif method_obj:
            self.name = method_obj.name_tmpl
        else:
            self.name = self.get_stmt_name(self.kind)

        self.is_unknown = self.name == "UNKNOWN" and not is_condition
        self.unique_name = uuid.uuid4()
        self.stmt_child = []
        self._is_condition = is_condition
        self.stmt_condition = None
        # self.contain_else = False
        self.end_stmt = None
        self.method_obj = method_obj

        if self.is_root():
            # start the stack for stmt_child
            stack_parent = [self]

        self._fill_end(cursor, stack_parent=stack_parent)
        self.add_before_stmt(before_stmt, stack_parent)
        self._fill_statement(cursor, count_stmt=count_stmt, stack_parent=stack_parent)

        if count_stmt is not None:
            count_stmt[self.name] += 1

        # exception for condition
        if is_condition:
            self.name = "condition"
        if self.kind in util.dct_alias_operator_stmt:
            self._construct_description()

    def _construct_description(self):
        for child in self.stmt_child:
            self.description += "%s %s\n" % (child.type, child.name_tmpl)
        # remove end line
        self.description = self.description.strip("\n")

    def _fill_end(self, cursor, stack_parent=None):
        if self.is_block_stmt() or self.is_root():
            if stack_parent[-1].kind is clang.cindex.CursorKind.IF_STMT:
                # get end_stmt of his parent "if" for "else if" stmt
                self.end_stmt = stack_parent[-1].end_stmt
            else:
                # create new end_stmt
                end_location = Location(cursor.extent.end)
                self.end_stmt = FakeStatement("end " + self.name, begin_stmt=self, location=end_location)

        if not self.is_root():
            # TODO optimise this stack_parent
            # add stmt on stack, ignore if root, because already in stack
            if self.is_block_stmt():
                stack_parent.append(self)

    def _fill_statement(self, cursor, count_stmt=None, stack_parent=None):
        before_stmt = self
        stmt = None
        lst_child = list(cursor.get_children())
        # keep trace on stmt condition to build next_stmt when child is instance
        i = 0
        for child in lst_child:
            i += 1
            # condition is first item of child and need to be a condition stmt
            is_condition = not stmt and self.kind in util.dct_alias_condition_stmt

            # else support
            if self.kind is clang.cindex.CursorKind.IF_STMT and i == 3:
                statement_before_stmt = ParentStatement.get_first_before_stmt(before_stmt)
            else:
                statement_before_stmt = before_stmt

            stmt = Statement(child, count_stmt=count_stmt, is_condition=is_condition, stack_parent=stack_parent,
                             before_stmt=statement_before_stmt)

            self.stmt_child.append(stmt)

            # keep reference of last child
            before_stmt = stmt.end_stmt if stmt.end_stmt else stmt

            if is_condition and not self.stmt_condition:
                self.stmt_condition = stmt

            if len(lst_child) == i and (self.is_compound() or self.is_block_stmt() or self.is_root()):
                # last child in block
                # ignore if the stmt is else. When last 2 child are compound
                if not (len(lst_child) == 3 and self.stmt_child[-1].is_compound() and self.stmt_child[-2].is_compound()):
                    self._add_before_stmt_in_child(stmt, stack_parent)

            # to optimize, don't continue with child if jump stmt
            # if stmt.kind in util.dct_alias_stmt_jump and not self.is_block_stmt():
            #     self._add_before_stmt_in_child(stmt, stack_parent)
            #     break

        if self.is_block_stmt():
            stack_parent.pop()

    def _add_before_stmt_in_child(self, stmt, stack_parent):
        # find last end of stmt block
        end_stmt = self.get_first_end_before_stmt(self, stack_parent)
        actual_stmt = stmt.end_stmt if stmt.is_block_stmt() else stmt
        if end_stmt:
            end_stmt.add_before_stmt(actual_stmt, stack_parent)
