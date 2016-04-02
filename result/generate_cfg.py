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
        self.g.node_attr.update(shape='circle')

        self._add_stmt_dot()

        self.g.layout(prog='circo')
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

    def _add_generic_node(self, cfg, key_label=""):
        # don't print if empty and no next or before stmt
        if not cfg or (not cfg.next_stmt and not cfg.before_stmt):
            return
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
