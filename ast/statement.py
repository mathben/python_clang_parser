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
        return bool(self.begin_stmt) and self.begin_stmt.end_stmt == self

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

    def is_stmt_jump(self):
        return self.kind in util.dct_alias_stmt_jump

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
        last_stmt = ParentStatement.get_last_stmt_from_stack(stack_parent, util.dct_alias_block_stmt)
        return last_stmt.end_stmt

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

    def add_stmt(self, next_stmt, condition=None):
        """Link stmt together with self and next_stmt. Use condition to add label for direction.
        """
        if isinstance(next_stmt, ParentStatement):
            ParentStatement._append_stmt(self.next_stmt, next_stmt, condition=condition)
            ParentStatement._append_stmt(next_stmt.before_stmt, self, condition=condition)
            print("TRACE before %s; next %s condition %s" % (self, next_stmt, condition))

    def add_before_stmt(self, stmt, stack_parent):
        # stmt can be dict(key, Statement) or Statement or list(Statement)
        # TODO stmt is self with return statement. It's an error.
        if self.is_unknown or not stmt or stmt.is_unknown or (stmt == self and stmt.is_block_stmt()):
            return

        if stmt.is_compound() and self.is_end():
            # exception, when we need to point last element in compound on exit block
            self.add_before_stmt(stmt.stmt_child[-1], stack_parent)
            return

        elif stmt.is_stmt_return():
            stmt.add_stmt(stack_parent[0].end_stmt)

        elif stmt.is_stmt_break():
            last_loop_stmt = self.get_last_stmt_from_stack(stack_parent, util.dct_alias_affected_break_stmt)
            stmt.add_stmt(last_loop_stmt.end_stmt)

        elif stmt.is_stmt_continue():
            last_loop_stmt = self.get_last_stmt_from_stack(stack_parent, util.dct_alias_affected_break_stmt)
            stmt.add_stmt(last_loop_stmt.stmt_condition)

        elif self.is_loop_stmt() and self.is_end() and not stmt.is_condition():
            stmt.add_stmt(self.begin_stmt.stmt_condition)

        else:
            b_condition = None
            if stmt.is_condition():
                # set condition branch
                if "True" not in stmt.next_stmt:
                    b_condition = "True"
                else:
                    b_condition = "False"
            stmt.add_stmt(self, condition=b_condition)

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
        elif is_condition:
            self.name = "condition"
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

        if self.is_unknown:
            return

        if not self.is_condition():
            self._fill_statement(cursor, count_stmt=count_stmt, stack_parent=stack_parent)

        if count_stmt is not None:
            count_stmt[self.name] += 1

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
        """Search child Statement. Link with before Statement.
        """
        before_stmt = self
        lst_child = list(cursor.get_children())
        # keep trace on stmt condition to build next_stmt when child is instance
        i = 0
        if self.is_block_stmt():
            # index 0 is condition
            # index 1 is next_stmt True condition
            # index 2 is next_stmt False condition [optional]
            if len(lst_child) < 2:
                print("Error, block stmt suppose to have greater or equal of 2 children.")
                return

            condition = Statement(lst_child[0], count_stmt=count_stmt, is_condition=True, stack_parent=stack_parent,
                                  before_stmt=self)
            self.stmt_condition = condition
            self.stmt_child.append(condition)

            stmt1 = Statement(lst_child[1], count_stmt=count_stmt, is_condition=False, stack_parent=stack_parent,
                              before_stmt=condition)
            self.stmt_child.append(stmt1)
            self.end_stmt.add_before_stmt(stmt1, stack_parent)

            if len(lst_child) == 3:
                stmt2 = Statement(lst_child[2], count_stmt=count_stmt, is_condition=False, stack_parent=stack_parent,
                                  before_stmt=condition)
                self.stmt_child.append(stmt2)
                # it's double link when it's else if, so ignore if it's block stmt
                if not stmt2.is_block_stmt():
                    self.end_stmt.add_before_stmt(stmt2, stack_parent)
            else:
                self.end_stmt.add_before_stmt(condition, stack_parent)

            stack_parent.pop()
            # no need to loop on child
            return

        elif self.is_stmt_jump():
            # because the next stmt in child will be ignore, add special jump stmt
            self.add_before_stmt(self, stack_parent)

        for child in lst_child:
            i += 1
            stmt = Statement(child, count_stmt=count_stmt, is_condition=False, stack_parent=stack_parent,
                             before_stmt=before_stmt)

            self.stmt_child.append(stmt)

            # keep reference of last child
            before_stmt = stmt.end_stmt if stmt.end_stmt else stmt

            # to optimize, don't continue with child if jump stmt
            if stmt.is_stmt_jump() and (self.is_compound() or self.is_root()):
                self.add_before_stmt(stmt, stack_parent)
                break
            # exception, when it's a block and some jump inside, ignore the rest of child
            if stmt.is_block_stmt() and not stmt.end_stmt.before_stmt:
                # remove end stmt, because no one point on it
                stmt.end_stmt = None
                break

    def _add_before_stmt_in_child(self, stmt, stack_parent):
        """Find last end of stmt block.
        Exception if stmt jump type
        """
        if stmt.is_unknown:
            return
        end_stmt = self.get_first_end_before_stmt(self, stack_parent)
        actual_stmt = stmt.end_stmt if stmt.is_block_stmt() else stmt
        if end_stmt:
            end_stmt.add_before_stmt(actual_stmt, stack_parent)
