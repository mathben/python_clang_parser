#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import pygraphviz as pgv
import csv
import os

from ast.clang_parser import clang
from ast import ast


class ClangParserCFG(object):
    def __init__(self, _parser, _lst_obj_ast):
        self._parser = _parser
        self._lst_obj_ast = _lst_obj_ast
        self._name = os.path.split(_parser.working_path)[1]
        self._cfg_name = "CFG " + self._name
        self.g = pgv.AGraph(name=self._cfg_name, directed=True)

    def generate_cfg(self):
        self.g.node_attr.update(shape='circle')

        self._add_stmt_dot()

        self.g.layout(prog='circo')
        self.g.draw(path=self._name + "_circo.svgz", format='svgz')

        self.g.write(self._name + ".dot")

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

    def _add_node(self, cfg):
        label = cfg.label() if not cfg.is_root() else "Entry " + cfg.label()
        if not cfg.is_compound():
            cfg_unique_name = cfg.unique_name
            # ignore compound in graph
            self.g.add_node(cfg_unique_name, label=label)

            if cfg.end_stmt:
                # Create end stmt
                end_stmt = cfg.end_stmt
                label = end_stmt.label() if not cfg.is_root() else "Exit " + end_stmt.label()
                self.g.add_node(end_stmt.unique_name, label=label)
                if end_stmt.next_stmt:
                    if cfg.is_block_stmt():
                        self.g.add_edge(end_stmt.unique_name, end_stmt.next_stmt.stmt_condition.unique_name,
                                        arrowhead="normal")
                    else:
                        self.g.add_edge(end_stmt.unique_name, end_stmt.next_stmt.unique_name, arrowhead="normal")
        else:
            # force to point on his parent, usually a condition
            cfg_unique_name = cfg.before_stmt.unique_name

        if cfg.next_stmt:
            if type(cfg.next_stmt) is dict:
                for key, value in cfg.next_stmt.items():
                    # get first element in compound if exist
                    unique_name = value.unique_name if not value.is_compound() else value.stmt_child[0].unique_name
                    self.g.add_edge(cfg_unique_name, unique_name, arrowhead="normal", label=key)
            else:
                self.g.add_edge(cfg_unique_name, cfg.next_stmt.unique_name, arrowhead="normal")

        last_child = None
        for c in cfg.stmt_child:
            if c.is_unknown:
                continue

            if not last_child:
                # first child, get parent operation
                last_unique_name = cfg_unique_name
            elif last_child.end_stmt:
                # if contain end stmt, point to it
                last_unique_name = last_child.end_stmt.unique_name
            else:
                # by default, get last operation
                last_unique_name = last_child.unique_name

            # link inter child
            if not c.is_compound():
                self.g.add_edge(last_unique_name, c.unique_name, arrowhead="normal")

            self._add_node(c)

            last_child = c

        if not cfg.stmt_child and cfg.is_root():
            # link together if no child and first level
            self.g.add_edge(cfg_unique_name, cfg.end_stmt.unique_name, arrowhead="normal")


class ClangParserUML(object):
    def __init__(self, _parser, _lst_obj_ast):
        self._parser = _parser
        self._lst_obj_ast = _lst_obj_ast
        self._name = os.path.split(_parser.working_path)[1]
        self._uml_name = "UML " + self._name
        self.g = pgv.AGraph(name=self._uml_name, directed=True)

    def generate_uml(self):
        self.g.node_attr.update(shape='record')

        self._add_class_dot()

        self.g.layout(prog='circo')
        self.g.draw(path=self._name + "_circo.svgz", format='svgz')

        self.g.write(self._name + ".dot")

    def _add_class_dot(self):
        # double loop to get all class
        dct_class_obj = ast.create_class_dict_from_lst_ast_obj(self._lst_obj_ast)
        for cls_obj in dct_class_obj.values():
            self._add_class_node(cls_obj)
        # need a first iteration to create node before create edge
        for cls_obj in dct_class_obj.values():
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


class ClangParserCSV(object):
    def __init__(self, _parser, _lst_obj_ast):
        self._parser = _parser
        self._lst_obj_ast = _lst_obj_ast
        # append data with csv_cursor_kind filter
        self._cursor_kind_filter = [clang.cindex.CursorKind.CLASS_DECL,
                                    clang.cindex.CursorKind.CLASS_TEMPLATE,
                                    clang.cindex.CursorKind.CXX_METHOD,
                                    clang.cindex.CursorKind.FUNCTION_TEMPLATE,
                                    clang.cindex.CursorKind.FUNCTION_DECL]
        self._header = ["ID", "NOM_DU_FICHIER", "NOM_DE_LA_CLASSE", "NOM_DE_LA_METHODE", "#IF", "#ELSE", "#SWITCH",
                        "#WHILE", "#FOR", "#BREAK", "#CONTINUE", "#RETURN", "#USING", "#VARIABLES_LOCALES"]

    def generate_stat(self):
        lst_line_result = []
        count_file = len(self._parser.files)

        if self._parser.debug and not self._parser.quiet:
            print("Generate statistic for csv output.")
            # this is the same of the else section, but with print debug
            i_file = 0
            for obj in self._lst_obj_ast:
                i_file += 1
                print("(%s/%s) File %s" % (i_file, count_file, obj[0]))
                for res in obj[2]:
                    print(res.to_string())
                    if res.kind in self._cursor_kind_filter:
                        lst_line_result.append(res)
                print  # beautiful end line!
        else:
            _results = [obj[2] for obj in self._lst_obj_ast]
            # create a line for each entity in result
            lst_line_result = [line for res in _results for line in res if line.kind in self._cursor_kind_filter]

        self._create_csv(self._parser.csv, lst_line_result)

    def _create_csv(self, filename, data):
        csv_id = 0

        if not self._parser.quiet:
            print("Creating csv on file '%s'" % filename)

        with open(filename, 'w') as csv_file:
            result = csv.writer(csv_file, delimiter=';', quotechar="", quoting=csv.QUOTE_NONE)
            result.writerow(self._header)

            for clang_obj in data:
                if clang_obj.kind in [clang.cindex.CursorKind.CLASS_DECL, clang.cindex.CursorKind.CLASS_TEMPLATE]:
                    # class section
                    for clang_obj_child in clang_obj.methods:
                        self.add_line(result, clang_obj, clang_obj_child, csv_id)
                        csv_id += 1
                else:
                    # method of function section
                    self.add_line(result, None, clang_obj, csv_id)
                    csv_id += 1

            if not self._parser.quiet:
                print("%s row into %s" % (csv_id, filename))

    @staticmethod
    def add_line(csv_file, obj_cls, obj_fct, csv_id):
        file_name = obj_fct.file_name[:]
        l = obj_fct.keywords
        lst_info = [csv_id, file_name, obj_cls.name if obj_cls else None, obj_fct.name, l["if"], l["else"], l["switch"],
                    l["while"], l["for"], l["break"], l["continue"], l["return"], l["using"], obj_fct.count_variable]
        csv_file.writerow(lst_info)
