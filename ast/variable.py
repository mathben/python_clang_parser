#!/usr/bin/env python2
# -*- coding: utf-8 -*-

# from ast_object import ASTObject


class ReachDefinition(object):
    @staticmethod
    def generate_reach_definition(cfg_root):
        lst_operator_var = cfg_root.generator_child(add_variable=True, field_name_not_empty="variable")
        lst_operator_var = [a.variable for a in lst_operator_var if not a.is_end()]

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

        # process IN and OUT
        ReachDefinition.process_reach_definition(cfg_root)

    @staticmethod
    def process_reach_definition(cfg_root):
        lst_stmt = cfg_root.generator_child()
        # 0 on all node
        for stmt in lst_stmt:
            if stmt.variable and not stmt.reach_definition:
                stmt.reach_definition = stmt.variable
            elif not stmt.reach_definition:
                stmt.reach_definition = OperatorVariable(stmt)

        has_change = True
        while has_change:
            has_change = False
            for stmt in lst_stmt:
                has_change |= stmt.reach_definition.process_reach_definition()


class OperatorVariable(object):
    def __init__(self, stmt, lst_declare=[], lst_gen=[]):
        self.stmt = stmt
        self.lst_declare = set(lst_declare)
        self.lst_gen = set(lst_gen)
        self.lst_var = set(lst_declare + lst_gen)
        self.kill = []

        self.reach_def_in = []
        self.reach_def_out = []

        for var in self.lst_var:
            var.set_operator_variable(self)

        self.lst_var_name = [a.name for a in self.lst_var]

    def process_reach_definition(self):
        stmt = self.stmt
        # IN
        # U EX[P]
        union_in = set()
        if stmt.before_stmt:
            for prec in [b for a in stmt.get_child(stmt.before_stmt) for b in list(a)]:
                if prec.reach_definition.reach_def_out:
                    last_out = prec.reach_definition.reach_def_out[-1]
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
