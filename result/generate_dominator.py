#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import pygraphviz as pgv
import os

from ast import ast
from ast import statement


class GenerateDominator(object):
    def __init__(self, _parser, _lst_obj_ast, is_dominator=True):
        self._parser = _parser
        self._lst_obj_ast = _lst_obj_ast
        self._name = os.path.split(_parser.working_path)[1]
        self.is_dominator = is_dominator

        if is_dominator:
            self.file_path = os.path.join(_parser.graph_path, self._name + ".dom.dot")
            self.file_path_svg = os.path.join(_parser.graph_path, self._name + ".dom.dot.svgz")
            self._cfg_name = "DOMINATOR " + self._name
            self.stmt_ref = statement.ref_stmt["dominator"]
        else:
            self.file_path = os.path.join(_parser.graph_path, self._name + ".post_dom.dot")
            self.file_path_svg = os.path.join(_parser.graph_path, self._name + ".post_dom.dot.svgz")
            self._cfg_name = "POST-DOMINATOR " + self._name
            self.stmt_ref = statement.ref_stmt["post_dominator"]

        self.g = pgv.AGraph(name=self._cfg_name, directed=True)

    def generate_dominator(self):
        self.g.node_attr.update(shape='circle')

        self._add_stmt_dot()

        self.g.layout(prog='dot')
        self.g.draw(path=self.file_path_svg, format='svgz')

        self.g.write(self.file_path)

    def _add_stmt_dot(self):
        # double loop to get all class
        lst_fct_obj = ast.create_function_list_from_lst_ast_obj(self._lst_obj_ast)
        for fct_obj in lst_fct_obj:
            if not fct_obj.enable_cfg:
                continue
            if fct_obj.is_valid_cfg:
                # create cfg node here!
                self._add_node([fct_obj.cfg if self.is_dominator else fct_obj.cfg.end_stmt], visited_node=[])

    def _add_node(self, lst_stmt, last_stmt=None, visited_node=None):
        for stmt in lst_stmt:
            if not stmt or stmt in visited_node:
                continue
            visited_node.append(stmt)

            self.g.add_node(stmt.unique_name, label=stmt.label())
            if last_stmt:
                self.g.add_edge(last_stmt.unique_name, stmt.unique_name, arrowhead="normal")
            self._add_node(getattr(stmt, self.stmt_ref["dom_next_stmt"]), last_stmt=stmt, visited_node=visited_node)
