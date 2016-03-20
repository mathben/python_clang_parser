#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from clang_parser import clang
from clang_parser import create_class_dict_from_lst_ast_obj
import pygraphviz as pgv
import csv
import os
import uuid


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
        dct_class_obj = create_class_dict_from_lst_ast_obj(self._lst_obj_ast)
        count_valid_method = 0
        count_invalid_method = 0
        for cls_obj in dct_class_obj.values():
            for cls_fct in cls_obj.methods:
                if not cls_fct.enable_cfg:
                    continue
                if cls_fct.is_valid_cfg:
                    self._add_node(cls_fct.cfg, cls_fct)
                    count_valid_method += 1
                else:
                    count_invalid_method += 1
        total_cfg = count_valid_method + count_invalid_method
        if total_cfg:
            ratio_valid_cfg = (count_valid_method / float(total_cfg)) * 100
        else:
            ratio_valid_cfg = 0.0

        print(
            "Info valid cfg %s %.2f%% on invalid cfg %s." % (count_valid_method, ratio_valid_cfg, count_invalid_method))

    def _add_node(self, cfg_list, cls_fct, lvl=0, parent_name=None, end_block_name=None, entry_name=None,
                  exit_name=None):
        if not entry_name:
            parent_name = entry_name = "%s_entry_%s" % (uuid.uuid4(), cls_fct.name)
            self.g.add_node(entry_name, label="Entry " + cls_fct.name)

        if not exit_name:
            end_block_name = exit_name = "%s_exit_%s" % (uuid.uuid4(), cls_fct.name)
            self.g.add_node(exit_name, label="Exit " + cls_fct.name)

        for c in cfg_list:
            self.g.add_node(c.unique_name, label=c.label())
            self.g.add_edge(parent_name, c.unique_name, arrowhead="normal")
            child_parent_name = c.unique_name

            if c.is_block_stmt():
                end_block_name = "end_block_%s" % uuid.uuid4()
                self.g.add_node(end_block_name, label="%sEnd" % c.name)

            if c.is_return():
                self.g.add_edge(c.unique_name, exit_name, arrowhead="normal")
            elif not c.stmt_child and c is cfg_list[-1]:
                self.g.add_edge(c.unique_name, end_block_name, arrowhead="normal")
            elif c.stmt_child and not c.is_operator():
                # previous_name = child_parent_name if not condition_name else condition_name
                previous_name = child_parent_name
                self._add_node(c.stmt_child, cls_fct, lvl=lvl + 1, parent_name=previous_name,
                               end_block_name=end_block_name, entry_name=entry_name, exit_name=exit_name)

            if c.is_block_stmt():
                parent_name = end_block_name
            else:
                parent_name = c.unique_name

        if not cfg_list and not lvl:
            # no stmt into this function
            self.g.add_edge(entry_name, exit_name, arrowhead="normal")


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
        dct_class_obj = create_class_dict_from_lst_ast_obj(self._lst_obj_ast)
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
