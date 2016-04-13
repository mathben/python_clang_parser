#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os

from clang_parser import clang
from clang_parser import CLANG_DEFAULT_ARG
from function import Function
from function import Method
from ast_class import Class

AST_EXT_FILE = ".ast"


def build_classes(cursor, filename, dir_name, arg_parser, is_first_call=True):
    result = []
    # ignore Cursor Kind
    all_kind = [clang.cindex.CursorKind.CLASS_DECL, clang.cindex.CursorKind.CLASS_TEMPLATE,
                clang.cindex.CursorKind.NAMESPACE, clang.cindex.CursorKind.FUNCTION_TEMPLATE,
                clang.cindex.CursorKind.FUNCTION_DECL, clang.cindex.CursorKind.CXX_METHOD]

    # not work with .hh and .cc in same time
    # TODO use os path function
    header_filename = filename[filename.rfind("/"):-3]
    children_cursor = [m for m in cursor.get_children() if m.location.file and dir_name in m.location.file.name and
                       header_filename in m.location.file.name and m.kind in all_kind]

    # TODO merge when method is not in class, but in namespace
    for c_child in children_cursor:
        if c_child.kind in [clang.cindex.CursorKind.CLASS_DECL, clang.cindex.CursorKind.CLASS_TEMPLATE]:
            # eliminate forward declaration class, if token size <= 3
            if len([t for t in c_child.get_tokens()]) > 3:
                cls = Class(c_child, arg_parser, filename=filename)
                result.append(cls)
        elif c_child.kind == clang.cindex.CursorKind.NAMESPACE:
            result.extend(build_classes(c_child, filename, dir_name, arg_parser, is_first_call=False))
        elif c_child.kind in [clang.cindex.CursorKind.FUNCTION_TEMPLATE, clang.cindex.CursorKind.FUNCTION_DECL,
                              clang.cindex.CursorKind.CXX_METHOD]:
            fct = Function(c_child, arg_parser, filename=filename)
            result.append(fct)

    # merge header with src
    if is_first_call:
        # merge with class first
        [cls.merge_method(result) for cls in result if isinstance(cls, Class)]
        # merge with other method
        result = merge_method(result)

    return result


def create_class_dict_from_lst_ast_obj(lst_ast_obj):
    # TODO need to fix class template, need to be merge with his cc file outside of the file :(
    # _filter = [clang.cindex.CursorKind.CLASS_DECL, clang.cindex.CursorKind.CLASS_TEMPLATE]
    _filter = [clang.cindex.CursorKind.CLASS_DECL]
    # double loop to get all class
    return {cls_obj.namespace_name: cls_obj for lst_clang_obj in lst_ast_obj for cls_obj in lst_clang_obj[2] if
            cls_obj.kind in _filter}


def create_function_list_from_lst_ast_obj(lst_ast_obj):
    _filter = [clang.cindex.CursorKind.FUNCTION_DECL]

    # get all method from class/namespace
    lst_met = [met_obj for cls_obj in create_class_dict_from_lst_ast_obj(lst_ast_obj).values()
               for met_obj in cls_obj.methods]
    # get all function outside of class
    lst_fct = [fct_obj for lst_clang_obj in lst_ast_obj for fct_obj in lst_clang_obj[2] if fct_obj.kind in _filter]
    return lst_fct + lst_met


def merge_method(lst_method):
    result = []
    for new_method in lst_method:
        if not isinstance(new_method, Function) and not isinstance(new_method, Method):
            result.append(new_method)
            continue

        if not new_method.mangled_name:
            result.append(new_method)
            continue

        for old_method in [m for m in result if isinstance(m, Function) or isinstance(m, Method)]:
            if new_method.mangled_name == old_method.mangled_name:
                old_method.merge(new_method)
                # no need to search a new brother
                break
        else:
            result.append(new_method)

    return result


def _path_to_filename(_path):
    split = os.path.split(_path)
    if not len(split[0]):
        return _path
    return _path_to_filename(split[0]) + "_" + split[1]


def clang_parser(arg):
    # TODO can we use unsaved_file with _clang_index.parse to improve performance?
    _file_name = os.path.normcase(arg[0])
    _dir_name = os.path.normcase(arg[1])
    _clang_arg = CLANG_DEFAULT_ARG + arg[2]
    _arg_parser = arg[3]
    _translation_unit = None

    _ast_file_exist = False
    _ast_file_path = ""

    if _arg_parser.translation_unit_dir:
        _ast_file_path = os.path.join(_arg_parser.translation_unit_dir, _path_to_filename(_file_name) + AST_EXT_FILE)
        _ast_file_exist = os.path.isfile(_ast_file_path)

    absolute_file_path = os.path.join(_dir_name, _file_name)
    # options = clang.cindex.TranslationUnit.PARSE_SKIP_FUNCTION_BODIES if _arg_parser.remove_token else 0
    options = clang.cindex.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD

    _obj_c_clang_index = clang.cindex.conf.lib.clang_createIndex(_arg_parser.exclude_decl_from_PCH,
                                                                 _arg_parser.show_missing_header_file)
    _clang_index = clang.cindex.Index(_obj_c_clang_index)

    # if _arg_parser.debug:
    #     print("Trace, execute ast for %s" % _ast_file_path)

    if _ast_file_exist:
        # load AST
        try:
            _translation_unit = clang.cindex.TranslationUnit.from_ast_file(_ast_file_path, index=_clang_index)
        except clang.cindex.TranslationUnitLoadError:
            # delete and try again
            print("Warning, cannot load file %s, recreate it." % _ast_file_path)
            os.remove(_ast_file_path)
            _ast_file_exist = False

    if not _ast_file_exist:
        # parse to generate AST
        _translation_unit = _clang_index.parse(absolute_file_path, _clang_arg, options=options)

        if _arg_parser.translation_unit_dir:
            # save AST file
            _translation_unit.save(_ast_file_path)

    # build hierarchy
    _result = build_classes(_translation_unit.cursor, _file_name, _dir_name, _arg_parser)

    return _file_name, _clang_arg, _result
