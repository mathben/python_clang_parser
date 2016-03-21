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
        self._is_condition = False
        self.method_obj = None
        self.name = ""
        self.location = Location(None)

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

    def label(self):
        desc = "" if not self.description else "\n%s" % self.description
        return "%s\nline %s%s" % (self.name, self.location.line, desc)

    def has_from_recursive(self, stmt=None):
        # return true if find root before stmt, else return false
        if stmt is None:
            return self.has_from_recursive(self)
        if isinstance(stmt, dict):
            result = False
            # accumulate result, return true if find at least one true
            for obj_stmt in [obj for lst_stmt in stmt.values() for obj in lst_stmt]:
                result |= self.has_from_recursive(obj_stmt)
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

    def add_before_stmt(self, stmt, stack_parent):
        # stmt can be dict(key, Statement) or Statement or list(Statement)
        def _append_stmt(dct_stmt, _stmt, condition=None):
            if not (isinstance(_stmt, ParentStatement) and isinstance(dct_stmt, dict)):
                return
            if not dct_stmt or condition not in dct_stmt:
                dct_stmt[condition] = [_stmt]
            else:
                dct_stmt[condition].append(_stmt)

        def _add_stmt(before_stmt, next_stmt, before_condition=None, next_condition=None):
            if isinstance(next_stmt, ParentStatement) and isinstance(before_stmt, ParentStatement):
                if not(before_stmt.is_condition() and next_stmt.is_compound()):
                    _append_stmt(before_stmt.next_stmt, next_stmt, condition=before_condition)
                _append_stmt(next_stmt.before_stmt, before_stmt, condition=next_condition)
                # TODO do we need to remove compound
                # ignore this, because his before will be fill further
                # if not next_stmt.is_compound():
                #     _append_stmt(next_stmt.before_stmt, before_stmt)

        if not stmt or stmt.is_unknown or self.is_unknown:
            return
        if stmt.is_compound():
            # compound has always 1 before_stmt
            b_stmt = self.get_first_before_stmt(stmt)
            b_condition = None
            if b_stmt.is_condition():
                if "True" not in b_stmt.next_stmt:
                    b_condition = "True"
                else:
                    b_condition = "False"
            _add_stmt(b_stmt, self, before_condition=b_condition)
        elif stmt.is_stmt_return():
            _add_stmt(stmt, stack_parent[0].end_stmt)
        else:
            _add_stmt(stmt, self)

            # elif self.is_stmt_break():
            #     # exit last block end stmt of switch or loop stmt
            #     last_stmt = self.get_last_stmt_from_stack(stack_parent, util.dct_alias_affected_break_stmt)
            #     if last_stmt:
            #         self.next_stmt = last_stmt.end_stmt
            # elif self.is_stmt_continue():
            #     # go to last block of switch or loop stmt
            #     last_stmt = self.get_last_stmt_from_stack(stack_parent, util.dct_alias_affected_break_stmt)
            #     self.next_stmt = last_stmt.stmt_condition

    def __repr__(self):
        return "'%s' l %s" % (self.name, self.location.line)


class FakeStatement(ParentStatement):
    def __init__(self, name, begin_stmt=None, location=None, next_stmt=None):
        super(FakeStatement, self).__init__()
        self.name = name
        self.location = location
        self.begin_stmt = begin_stmt
        self.unique_name = uuid.uuid4()
        # self.next_stmt = next_stmt
        self.kind = None
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
            self.name = self.get_stmt_name(cursor.kind)

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

        self.add_before_stmt(before_stmt, stack_parent)

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

        if not self.is_root():
            # TODO optimise this stack_parent
            # add stmt on stack, ignore if root, because already in stack
            if self.is_block_stmt():
                stack_parent.append(self)

        before_stmt = self
        stmt = None
        lst_child = list(cursor.get_children())
        # keep trace on stmt condition to build next_stmt when child is instance
        lst_condition_child = []
        i = 0
        for child in lst_child:
            i += 1
            # condition is first item of child and need to be a condition stmt
            is_condition = not stmt and cursor.kind in util.dct_alias_condition_stmt
            # if before_stmt.is_compound():
            #     good_before_stmt = before_stmt.before_stmt
            # else:
            #     good_before_stmt = before_stmt

            stmt = Statement(child, count_stmt=count_stmt, is_condition=is_condition, stack_parent=stack_parent,
                             before_stmt=before_stmt)
            self.stmt_child.append(stmt)

            # if not before_stmt.next_stmt and not stmt.is_unknown:
            # if before_stmt.is_compound():
            #     before_stmt.before_stmt.next_stmt = stmt
            # else:
            #     before_stmt.next_stmt = stmt

            before_stmt = stmt.end_stmt if stmt.end_stmt else stmt

            if is_condition:
                if not self.stmt_condition:
                    self.stmt_condition = stmt
                lst_condition_child.append(stmt)

            # last child in block
            if len(lst_child) == i and (self.is_compound() or self.is_block_stmt() or self.is_root()):
                if self.is_root():
                    pass
                # find last end of stmt block
                end_stmt = self.get_first_end_before_stmt(self, stack_parent)
                if end_stmt:
                    end_stmt.add_before_stmt(stmt, stack_parent)

        if lst_condition_child:
            # TODO what we do we many condition? else?
            if len(lst_condition_child) > 1:
                print("ERROR, find many condition child and only take first.")
                # last_child = self.get_first_stmt_child(reversed(self.stmt_child))
                # self.end_stmt.add_before_stmt(last_child, stack_parent)
                # self.stmt_condition.next_stmt = {"False": self.end_stmt, "True": first_child}

        # get the last stmt of block (child) to point on his parent end_stmt
        # if stmt and not stmt.next_stmt and not stmt.is_unknown \
        #         and not stmt.is_compound() \
        #         and stmt.is_operator():
        #     # don't point to a compound stmt, get last block stmt
        #     stmt.next_stmt = self.get_last_stmt_from_stack(stack_parent, util.dct_alias_block_stmt).end_stmt
        if self.is_block_stmt():
            stack_parent.pop()
            # all node need a next_stmt and from_stmt
