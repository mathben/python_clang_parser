#!/usr/bin/env python2
# -*- coding: utf-8 -*-
import csv

from clang_parser import clang


def create_csv(lst_obj_ast):
    csv_filename_result = "result.csv"
    csv_id = 0
    header = ["ID", "NOM_DU_FICHIER", "NOM_DE_LA_CLASSE", "NOM_DE_LA_METHODE", "#IF", "#ELSE", "#SWITCH", "#WHILE",
              "#FOR", "#BREAK", "#CONTINUE", "#RETURN", "#USING", "#VARIABLES_LOCALES"]

    def add_line(c, cc, csv_id):
        file_name = cc.file_name[:]
        l = cc.keywords
        lst_info = [csv_id, file_name, c.name if c else None, cc.name, l["if"], l["else"], l["switch"],
                    l["while"], l["for"], l["break"], l["continue"], l["return"], l["using"], cc.count_variable]
        result.writerow(lst_info)

    print("Creating csv on file '%s'" % csv_filename_result)

    with open(csv_filename_result, 'w') as csvfile:
        result = csv.writer(csvfile, delimiter=';', quotechar="", quoting=csv.QUOTE_NONE)
        result.writerow(header)

        for c in lst_obj_ast:
            if c.kind in [clang.cindex.CursorKind.CLASS_DECL, clang.cindex.CursorKind.CLASS_TEMPLATE]:
                for cc in c.methods:
                    add_line(c, cc, csv_id)
                    csv_id += 1
            else:
                add_line(None, c, csv_id)
                csv_id += 1

        print("%s row into %s" % (csv_id, csv_filename_result))
