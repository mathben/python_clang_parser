#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from ast.clang_parser import clang
import csv


class GenerateStatCsv(object):
    def __init__(self, _parser, _lst_obj_ast):
        self._parser = _parser
        self._lst_obj_ast = _lst_obj_ast
        self._option_open_file = "a" if self._parser.append_csv else "w"
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

        with open(filename, self._option_open_file) as csv_file:
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
