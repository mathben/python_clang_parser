#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import pygraphviz as pgv
import os

from ast import ast


class GenerateCfg(object):
    def __init__(self, _parser, _lst_obj_ast):
        self._parser = _parser
        self._lst_obj_ast = _lst_obj_ast
        self._name = os.path.split(_parser.working_path)[1]
        self.file_path = os.path.join(_parser.graph_path, self._name + ".dot")
        self._cfg_name = "CFG " + self._name
        self.g = pgv.AGraph(name=self._cfg_name, directed=True)

    def generate_cfg(self):
        self.g.node_attr.update(shape='record')

        self._add_stmt_dot()

        self.g.layout(prog='dot')
        self.g.draw(path=self.file_path + "_circo.svgz", format='svgz')

        self.g.write(self.file_path)

    def _add_stmt_dot(self):
        # double loop to get all class
        lst_fct_obj = ast.create_function_list_from_lst_ast_obj(self._lst_obj_ast)
        count_valid_method = 0
        count_invalid_method = 0
        for fct_obj in lst_fct_obj:
            if not fct_obj.enable_cfg:
                continue
            if fct_obj.is_valid_cfg:
                # create cfg node here!
                self._add_node(fct_obj.cfg)
                count_valid_method += 1
            else:
                count_invalid_method += 1
        total_cfg = count_valid_method + count_invalid_method
        if total_cfg:
            ratio_valid_cfg = (count_valid_method / float(total_cfg)) * 100
        else:
            ratio_valid_cfg = 0.0

        print("Info valid cfg %s %.2f%% on invalid cfg %s." % (count_valid_method, ratio_valid_cfg,
                                                               count_invalid_method))

    @staticmethod
    def _build_label(cfg, key_label):
        label = key_label if cfg.is_root() else ""
        order = "#%s - " % cfg.order_id if cfg.order_id != -1 else ""
        str_grid = """
                <<table border="0" cellborder="1" cellspacing="0">
                   <tr><td port="a" bgcolor="#D0D0D0" colspan="4">%s%s %s <font color="green">line %s</font></td></tr>
        """.strip() % (order, label, cfg.name, cfg.location.line)

        if cfg.operator_variable:
            var_cfg = cfg.operator_variable
            var_str = ""
            if var_cfg.lst_var:
                var_str = " ".join(var_cfg.lst_var_link_name())

            var_use_str = ""
            if var_cfg.lst_use:
                # var_use_str = " ".join(var_cfg.lst_use_name())
                var_use_str = var_cfg.lst_use_name_link()

            if var_use_str or var_str:
                str_grid += """
                           <tr><td port="f">%s</td><td port="g">%s</td><td port="h">%s</td><td port="i">%s</td></tr>
                """.strip() % ("Var" if var_str else "", var_str, "Use" if var_use_str else "", var_use_str)

            if var_cfg.lst_var:
                gen_str = " ".join(var_cfg.lst_gen_name())
                if not gen_str:
                    gen_str = "-"

                kill_str = " ".join(var_cfg.lst_kill_name())
                if not kill_str:
                    kill_str = "-"

                str_grid += """
                           <tr><td port="b">Gen</td><td port="c">%s</td><td port="d">Kill</td><td port="e">%s</td></tr>
                """.strip() % (gen_str, kill_str)

            if var_cfg.reach_def_in:
                reach_def_in_str = " ".join(var_cfg.lst_reach_def_in_name())
                if not reach_def_in_str:
                    reach_def_in_str = "-"

                reach_def_out_str = " ".join(var_cfg.lst_reach_def_out_name())
                if not reach_def_out_str:
                    reach_def_out_str = "-"

                nb_iteration = len(var_cfg.reach_def_in)

                str_grid += """
                           <tr><td port="j">Reach def IN (%s)</td><td port="l">%s</td>
                           <td port="k">Reach def OUT</td><td port="m">%s</td></tr>
                """.strip() % (nb_iteration, reach_def_in_str, reach_def_out_str)

        str_grid += """
                </table>>
        """.strip()

        return str_grid

    def _add_generic_node(self, cfg, key_label=""):
        # don't print if empty and no next or before stmt
        if not cfg or (not cfg.next_stmt and not cfg.before_stmt):
            return
        if self._parser.show_detailed_cfg:
            self.g.add_node(cfg.unique_name, label=self._build_label(cfg, key_label))
        else:
            label = cfg.label() if not cfg.is_root() else key_label + cfg.label()
            self.g.add_node(cfg.unique_name, label=label)

        for key, lst_value in cfg.next_stmt.items():
            for value in lst_value:
                # add link
                label = ""
                color = ""
                if key:
                    label = key
                    if key == "True":
                        color = "green"
                    elif key == "False":
                        color = "red"

                self.g.add_edge(cfg.unique_name, value.unique_name, arrowhead="normal", label=label, color=color)

    def _add_node(self, cfg):
        # begin stmt
        self._add_generic_node(cfg, "Entry ")

        # end stmt
        self._add_generic_node(cfg.end_stmt, "Exit ")

        # create node for child
        for stmt in cfg.stmt_child:
            self._add_node(stmt)
