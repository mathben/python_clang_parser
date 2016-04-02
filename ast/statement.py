#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import uuid

from ast_object import ASTObject
from clang_parser import clang
from location import Location
import util

# use this ref to reverse walk over stmt
ref_stmt = {
    "dominator": {
        "before_stmt": "before_stmt",
        "next_stmt": "next_stmt",
        "begin_stmt": "begin_stmt",
        "end_stmt": "end_stmt",
        "dom_next_stmt": "dom_next_stmt",
        "dom_parent_stmt": "dom_parent_stmt"
    },
    "post_dominator": {
        "before_stmt": "next_stmt",
        "next_stmt": "before_stmt",
        "begin_stmt": "end_stmt",
        "end_stmt": "begin_stmt",
        "dom_next_stmt": "post_dom_next_stmt",
        "dom_parent_stmt": "post_dom_parent_stmt"
    }
}


class ParentStatement(object):
    def __init__(self, *args, **kwargs):
        super(ParentStatement, self).__init__()
        self.description = ""

        self.before_stmt = {}
        self.next_stmt = {}
        self.begin_stmt = None
        self.end_stmt = None

        self.dom_next_stmt = set()
        self.dom_parent_stmt = None

        self.post_dom_next_stmt = set()
        self.post_dom_parent_stmt = None

        self._is_condition = False
        self.method_obj = None
        self.name = ""
        self.location = Location(None)
        self.result_has_from_recursive = None

        self.order_id = -1

        # only Statement
        self.stmt_child = []

    def generator_child(self, ignore_unknown=True, ignore_empty_child=True, ignore_empty_cfg_child=True):
        # TODO use yield and not this wrong technique
        lst = [self] if ignore_empty_cfg_child and self.has_cfg_child() else []
        for stmt in self.stmt_child:
            if ignore_unknown and stmt.is_unknown:
                continue
            # if ignore_empty_child and not stmt.has_cfg_child():
            #     continue
            # if ignore_empty_cfg_child and not stmt.has_cfg_child(check_before_child=False, check_next_child=False):
            #     continue
            lst.extend(stmt.generator_child())
        if self.end_stmt:
            lst.append(self.end_stmt)
        return lst

    def has_cfg_child(self, check_before_child=True, check_next_child=True, condition=False):
        """
        :param check_before_child: bool check if has before_child
        :param check_next_child: bool check if has next_child
        :param condition: filter by None or str. If False, ignore it.
        :return: bool if has child depend of param filter
        """
        result = False
        if check_before_child and self.before_stmt:
            if condition is False:
                result = True
                # elif condition in self.before_stmt:
                #     result
        elif check_next_child and self.next_stmt:
            if condition is False:
                result = True
        return result

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

    @staticmethod
    def remove_compound(stmt):
        # this function remove compound stmt
        if not stmt:
            return
        if stmt.is_compound():
            # we remove the actual stmt, but all before stmt will point on next stmt
            for key, value in stmt.before_stmt.items():
                for b_stmt in value:
                    # usually 1 loop and key is True
                    b_stmt.next_stmt[key] = stmt.next_stmt[None]
                    for n_value in stmt.next_stmt[None]:
                        # None is from compound, now it's the from the new key
                        del n_value.before_stmt[None]
                        n_value.before_stmt[key] = value
            # erase before and next stmt for compound
            stmt.before_stmt = {}
            stmt.next_stmt = {}
        for stmt_child in stmt.stmt_child:
            ParentStatement.remove_compound(stmt_child)

    @staticmethod
    def count_total_stmt(dct_stmt):
        return sum([len(a) for a in dct_stmt.values()])

    def label(self):
        desc = "" if not self.description else "\n%s" % self.description
        order = "#%s - " % self.order_id if self.order_id != -1 else ""
        return "%s%s\nline %s%s" % (order, self.name, self.location.line, desc)

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
                elif isinstance(stmt_obj, list) or isinstance(stmt_obj, set):
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

        info_from = generic_info(self.before_stmt, "from")
        info_to = generic_info(self.next_stmt, "to")
        contain_info = info_from or info_to
        info_dom = " - dom %s" % self.dom_next_stmt if contain_info and self.dom_next_stmt else ""
        info_post_dom = " - post-dom %s" % self.post_dom_next_stmt if contain_info and self.post_dom_next_stmt else ""
        order = " - #%s" % self.order_id if self.order_id != -1 else ""
        tuple_info = (order, info_from, info_to, info_dom, info_post_dom)
        return "%s%s%s%s%s" % tuple_info

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
            # TODO we need to create set to remove duplication, find why?
            dct_stmt[condition] = set([_stmt])
        else:
            dct_stmt[condition].add(_stmt)

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
                b_condition = "False" if "True" in stmt.next_stmt else "True"
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
        order = "#%s - " % self.order_id if self.order_id != -1 else ""
        return "%s%s\nline %s" % (order, self.name, self.location.line)

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

        if self.is_root():
            self.remove_compound(stmt=self)
            # generate node of dominator
            self._generate_dominator_cfg(stmt=self, visited_stmt=[], ref_key="dominator")
            # generate node of post-dominator
            self._generate_dominator_cfg(stmt=self.end_stmt, visited_stmt=[], ref_key="post_dominator")
            # add order id to verbose debug
            self._add_order_id()

    def _add_order_id(self):
        order_id = 0
        lst_generator_child = self.generator_child()
        for stmt in lst_generator_child:
            order_id += 1
            stmt.order_id = order_id

    @staticmethod
    def _get_dominator_parent_stack(stmt, ref_key="dominator"):
        stmt_ref = ref_stmt[ref_key]
        # TODO use lambda
        if not stmt:
            return
        stack_stmt = [stmt]
        stmt = getattr(stmt, stmt_ref["dom_parent_stmt"])
        while stmt:
            stack_stmt.append(stmt)
            stmt = getattr(stmt, stmt_ref["dom_parent_stmt"])

        return stack_stmt

    @staticmethod
    def _find_first_common_stmt(stack_parent, lst_stmt, lst_visited_stmt, ref_key="dominator"):
        for stmt in lst_stmt:
            if stmt in lst_visited_stmt:
                continue
            if stmt in stack_parent:
                return stmt
            # TODO bug with visited, this solution not work, maybe need an iterator
            lst_visited_stmt.append(stmt)
            lst_before_stmt = [b for a in getattr(stmt, ref_stmt[ref_key]["before_stmt"]).values() for b in a]
            return_stmt = Statement._find_first_common_stmt(stack_parent, lst_before_stmt, lst_visited_stmt,
                                                            ref_key="dominator")
            if return_stmt:
                return return_stmt

    @staticmethod
    def _generate_dominator_cfg(stmt=None, parent_stmt=None, visited_stmt=None, ref_key="dominator"):
        """This function search dominator or post-dominator. Use ref_key to implement reverse."""
        stmt_ref = ref_stmt[ref_key]
        # exit if stmt is None or already find dominator next stmt
        if not stmt or getattr(stmt, stmt_ref["dom_next_stmt"]):
            return

        if ParentStatement.count_total_stmt(getattr(stmt, stmt_ref["before_stmt"])) > 1:
            # need to find who is the nearest stmt
            lst_before_stmt = [b for a in getattr(stmt, stmt_ref["before_stmt"]).values() for b in a if
                               b != parent_stmt]
            stack_parent = Statement._get_dominator_parent_stack(parent_stmt, ref_key=ref_key)

            new_parent_stmt = Statement._find_first_common_stmt(stack_parent, lst_before_stmt, [], ref_key=ref_key)
            if not new_parent_stmt:
                print("Error, %s cannot find common parent of stmt %s" % (ref_key, stmt))
            elif new_parent_stmt != parent_stmt:
                if stmt in getattr(parent_stmt, stmt_ref["dom_next_stmt"]):
                    getattr(parent_stmt, stmt_ref["dom_next_stmt"]).remove(stmt)
                parent_stmt = new_parent_stmt
                getattr(parent_stmt, stmt_ref["dom_next_stmt"]).add(stmt)

        elif not getattr(stmt, stmt_ref["before_stmt"]) and not stmt.is_root():
            print("Error, %s all cfg stmt node suppose to have before_stmt, %s.", (ref_key, stmt))
            return

        if stmt in visited_stmt:
            return
        print("Trace %s add %s" % (ref_key, stmt))
        visited_stmt.append(stmt)
        # merge list from list/list
        setattr(stmt, stmt_ref["dom_parent_stmt"], parent_stmt)
        # example, [[a, b], [c, d]] -> [a, b, c, d]
        lst_next_stmt = [b for a in getattr(stmt, stmt_ref["next_stmt"]).values() for b in a]
        # for all stmt, find dominator
        for next_stmt in lst_next_stmt:
            getattr(stmt, stmt_ref["dom_next_stmt"]).add(next_stmt)
            Statement._generate_dominator_cfg(next_stmt, parent_stmt=stmt, visited_stmt=visited_stmt, ref_key=ref_key)

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
                # this link the end of block when if alone or while
                self.end_stmt.add_before_stmt(condition, stack_parent)

            stack_parent.pop()
            # no need to loop on child
            return

        elif self.is_stmt_jump():
            # because the next stmt in child will be ignore, add special jump stmt
            self.add_before_stmt(self, stack_parent)

        for child in lst_child:
            i += 1
            # ignore stmt chain when parent is not a block or root
            if not self.is_block_stmt() and not self.is_compound() and not self.is_root():
                before_stmt = None

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

        # this fix when no return in function, link with last child
        if self.is_root():
            self.end_stmt.add_before_stmt(stmt, stack_parent)

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
