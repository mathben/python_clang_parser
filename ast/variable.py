#!/usr/bin/env python2
# -*- coding: utf-8 -*-

# from ast_object import ASTObject
from collections import defaultdict


class ReachDefinition(object):
    @staticmethod
    def generate_reach_definition(cfg_root):
        lst_operator_var = cfg_root.generator_child(add_variable=True, field_name_not_empty="operator_variable")
        lst_operator_var = [a.operator_variable for a in lst_operator_var if not a.is_end()]

        id_def = 0
        lst_unique_var_gen = []
        # create unique list
        for op_var in lst_operator_var:
            for var in op_var.lst_var:
                var.id = id_def
                lst_unique_var_gen.append(var)
                id_def += 1

        # create gen and kill
        for op_var in lst_operator_var:
            op_var.set_lst_unique_var_gen(lst_unique_var_gen)

        # prepare variable for each node
        # 0 on all node
        lst_stmt = cfg_root.generator_child()
        for stmt in lst_stmt:
            if not stmt.operator_variable:
                stmt.operator_variable = OperatorVariable(stmt)

        # process IN and OUT
        ReachDefinition.process_reach_definition(lst_stmt)

        # data dependency
        ReachDefinition.process_data_dependency(lst_stmt, lst_operator_var)

    @staticmethod
    def process_reach_definition(lst_stmt):
        has_change = True
        while has_change:
            has_change = False
            for stmt in lst_stmt:
                has_change |= stmt.operator_variable.process_reach_definition()

    @staticmethod
    def process_data_dependency(lst_stmt, lst_stmt_gen):
        # find gen dependency on use variable
        for stmt in lst_stmt:
            if stmt.operator_variable.lst_use:
                lst_use = stmt.operator_variable.lst_use

                for var in lst_use:
                    # find association with lst_stmt_gen
                    for stmt_gen in lst_stmt_gen:
                        for name, gen_var in stmt_gen.lst_gen_name_link():
                            if var.name == name:
                                stmt.operator_variable.lst_use_link[var.name].append(gen_var)


class OperatorVariable(object):
    def __init__(self, stmt, lst_declare=[], lst_gen=[], lst_use=[]):
        self.stmt = stmt
        self.lst_var = set(lst_declare + lst_gen)
        self.lst_use = []
        self.kill = []

        self.reach_def_in = []
        self.reach_def_out = []
        self.lst_use_link = defaultdict(list)

        self.set_lst_use(lst_use)

        for var in self.lst_var:
            var.set_operator_variable(self)

        self.lst_var_name = [a.name for a in self.lst_var]

    def set_lst_use(self, lst_use):
        for var_use in lst_use:
            if var_use not in self.lst_use:
                self.lst_use.append(var_use)

    def process_reach_definition(self):
        stmt = self.stmt
        # IN
        # U EX[P]
        union_in = set()
        if stmt.before_stmt:
            for last_stmt in [b for a in stmt.get_child(stmt.before_stmt) for b in list(a)]:
                if last_stmt.operator_variable.reach_def_out:
                    last_out = last_stmt.operator_variable.reach_def_out[-1]
                    union_in.update(last_out)
        self.reach_def_in.append(union_in)
        # OUT
        # gen U (IN - kill)
        # TODO use difference_update

        in_kill = None
        if union_in:
            in_kill = union_in.copy()
            for var_kill in self.kill:
                in_kill.discard(var_kill)

        out = set()
        out.update(self.lst_var)
        if in_kill:
            out.update(in_kill)

        self.reach_def_out.append(out)

        # check has change
        if len(self.reach_def_in) < 2:
            return True
        # has_change = bool(self.reach_def_in[-2].difference(self.reach_def_in[-1]))
        # has_change |= bool(self.reach_def_out[-2].difference(self.reach_def_out[-1]))
        has_change = False
        for a in list(self.reach_def_in[-2]):
            if a not in self.reach_def_in[-1]:
                has_change = True
                break
        if not has_change:
            for a in list(self.reach_def_in[-1]):
                if a not in self.reach_def_in[-2]:
                    has_change = True
                    break
        if not has_change:
            for a in list(self.reach_def_out[-2]):
                if a not in self.reach_def_out[-1]:
                    has_change = True
                    break
        if not has_change:
            for a in list(self.reach_def_out[-1]):
                if a not in self.reach_def_out[-2]:
                    has_change = True
                    break
        return has_change

    def lst_var_link_name(self):
        return ["[%s-%s]" % (a.name, a.name_def()) for a in self.lst_var]

    def lst_kill_name(self):
        return sorted([a.name_def() for a in self.kill])

    def lst_gen_name(self):
        return sorted([a.name_def() for a in self.lst_var])

    def lst_gen_name_link(self):
        return sorted([(a.name, a) for a in self.lst_var])

    def lst_use_name(self):
        return sorted([a.name for a in self.lst_use])

    def lst_use_name_link(self):
        return ", ".join(
            ["%s - [%s]" % (key, " ".join([a.name_def() for a in value])) for key, value in self.lst_use_link.items()])

    def lst_reach_def_out_name(self):
        return sorted([a.name_def() for a in list(self.reach_def_out[-1])])

    def lst_reach_def_in_name(self):
        return sorted([a.name_def() for a in list(self.reach_def_in[-1])])

    def set_lst_unique_var_gen(self, lst):
        for var in lst:
            if var.op_var == self:
                continue
            if var.name in self.lst_var_name:
                self.kill.append(var)

    def __repr__(self):
        return " ".join(list(self.lst_var))


class Variable(object):
    def __init__(self, stmt):
        super(Variable, self).__init__()
        self.stmt = stmt
        self.name = stmt.name_tmpl
        self.id = -1
        self.op_var = None

    def set_operator_variable(self, op_var):
        self.op_var = op_var

    def name_def(self):
        return "d%02d" % self.id

    def __eq__(self, other):
        return self.id == other.id

    def __repr__(self):
        return self.name
