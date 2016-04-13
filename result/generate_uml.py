#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
import pygraphviz as pgv

from ast import ast


class GenerateUml(object):
    def __init__(self, _parser, _lst_obj_ast):
        self._parser = _parser
        self._lst_obj_ast = _lst_obj_ast
        self._name = os.path.split(_parser.working_path)[1]
        self.file_path = os.path.join(_parser.graph_path, self._name + ".dot")
        self._uml_name = "UML " + self._name
        file_path = os.path.join(_parser.graph_path, self._uml_name)
        self.g = pgv.AGraph(name=file_path, directed=True)

    def generate_uml(self):
        self.g.node_attr.update(shape='record')

        self._add_class_dot()

        self.g.layout(prog='dot')
        self.g.draw(path=self.file_path + "_dot.svgz", format='svgz')

        self.g.write(self.file_path)

    def _add_class_dot(self):
        # double loop to get all class
        dct_class_obj = ast.create_class_dict_from_lst_ast_obj(self._lst_obj_ast)
        for cls_obj in dct_class_obj.values():
            self._add_class_node(cls_obj)
            self._add_class_base_edge(cls_obj)
            self._add_class_composition_edge(cls_obj)

    def _add_class_node(self, cls_obj):
        self.g.add_node(cls_obj.namespace_name, label=cls_obj.get_dot())

    def _add_class_base_edge(self, cls_obj):
        for cls_base in cls_obj.derived_class:
            if not self.g.has_node(cls_base.type):
                # create a external node
                self.g.add_node(cls_base.type, color="red")
            self.g.add_edge(cls_obj.namespace_name, cls_base.type, arrowhead="empty")

    def _add_class_composition_edge(self, cls_obj):
        for var in cls_obj.variable:
            if not self.g.has_node(var.type):
                # create a external node
                # self.g.add_node(var.type, color="red")
                continue
            self.g.add_edge(cls_obj.namespace_name, var.type, arrowhead="normal")
