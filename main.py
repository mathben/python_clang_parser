#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
from glob import glob
import argparse
import time
import datetime
from multiprocessing import Pool

# local import
from ast import ast
import result

AST_EXT_FILE = ".ast"
CSV_EXT_FILE = ".csv"
CPP_EXT_FILE = ("*.cc", "*.cpp")


# TODO support sigterm and close all thread

def parse_args():
    _arg_parser = argparse.ArgumentParser(description="Python clang analyser c++")

    _arg_parser.add_argument('-q', '--quiet', default=False, action='store_true',
                             help='Silence all verbose print.')

    group = _arg_parser.add_argument_group("Debug")
    group.add_argument('-d', '--debug', default=False, help='Enable debug', action='store_true')
    group.add_argument('--show_missing_header_file', default=False, help='Show when Clang cannot find header file.',
                       action='store_true')
    group.add_argument('--remove_token', default=False, action='store_true',
                       help='We need token to retrieve the algorithm or condition statistic.')
    group.add_argument('--exclude_decl_from_PCH', default=False, action='store_true',
                       help='Exclude local declarations from PCH in translation unit when parsing with Clang. '
                            'No difference when debug or on performance execution if not using PCH file.')

    group = _arg_parser.add_argument_group("Parallelism")
    group.add_argument('--disable_threading', default=False, action='store_true',
                       help='Disable multi-process execution.')
    group.add_argument('-i', '--nb_cpu', default=None, type=int,
                       help='Default value is max cpu. Specify the count cpu usage.')

    group = _arg_parser.add_argument_group("Compilation")
    group.add_argument('-I', '--include_clang',
                       help='Add include file or directory. Separate each with \';\'. '
                            'Include can be absolute or relative from root_directory.')
    group.add_argument('--find_include', default=False, action='store_true',
                       help='If active, search include file in root_directory.')

    group = _arg_parser.add_argument_group("Configuration")
    group.add_argument('--root_directory', required=True,
                       help='Path of root directory. This path is use to filter files from '
                            'this directory only and set the working_path is not specified.')
    group.add_argument('--working_path',
                       help='Specify path of file or directory. Need to exist into root_directory. '
                            'If not specified, working_path will be root_directory.')
    group.add_argument('--graph_path', default="graph",
                       help='Specify path of graph generation.')
    group.add_argument('--translation_unit_dir',
                       help='Specify path of translation unit directory where to save AST file generate by Clang. '
                            'The parser will use the saving file if exist. '
                            'To force update AST files, we clean all. Use argument --clean_ast. '
                            'This feature improve parsing speed. '
                            'If AST file not exist for a specific source, it will generate it.')
    group.add_argument('--clean_ast', default=False, action='store_true',
                       help='Clean ast files from --translation_unit_dir before create it.')

    group = _arg_parser.add_argument_group("Statistic")
    group.add_argument('--generate_csv_stat', default=False, action='store_true',
                       help='Generate statistic of each function and method. Write output in csv file. '
                            'The statistic is the variable number and c++ token like [if, while, return, ...]. '
                            'See --csv_stat_name to change the output name file.')
    group.add_argument('--csv', default="result" + CSV_EXT_FILE,
                       help='Output csv name file of statistic generation. Add extension %s if not set.' % CSV_EXT_FILE)

    group = _arg_parser.add_argument_group("UML")
    group.add_argument('--generate_uml', default=False, action='store_true',
                       help='Generate UML of relation between class.')

    group = _arg_parser.add_argument_group("Control Flow")
    group.add_argument('--generate_control_flow', default=False, action='store_true',
                       help='Generate control flow from main function.')
    group.add_argument('--generate_dominator', default=False, action='store_true',
                       help='Generate dominator and post-dominator graph from control flow.')

    return _arg_parser


def validate_parser(_arg_parser):
    _parser = _arg_parser.parse_args()
    _parser.ast_file = []

    # validate argument
    # root directory
    if not os.path.isdir(_parser.root_directory):
        _arg_parser.print_help()
        raise ValueError("--root_directory '%s' is not a valid directory" % _parser.root_directory)

    # force to clean path, like remove last /
    _root_dir = _parser.root_directory = os.path.abspath(_parser.root_directory)

    # working path
    if not _parser.working_path:
        _parser.working_path = _root_dir
    elif _root_dir in _parser.working_path:
        if not os.path.exists(_parser.working_path):
            _arg_parser.print_help()
            raise ValueError("--working_path '%s' is not a valid directory or file." % _parser.working_path)
    else:
        new_path = os.path.abspath(os.path.join(_root_dir, _parser.working_path))
        if os.path.exists(new_path):
            _parser.working_path = new_path
        else:
            val = _parser.working_path, _root_dir
            raise ValueError("--working_path '%s' not exist in root_directory '%s'." % val)

    # Functionality
    if _parser.generate_csv_stat:
        if _parser.csv[-len(CSV_EXT_FILE):] != CSV_EXT_FILE:
            _parser.csv += CSV_EXT_FILE
        # validate if can open it
        try:
            open(_parser.csv).close()
        except:
            raise ValueError("--csv %s is wrong or maybe you don't access to write a file." % _parser.csv)

    # translation unit path saving files
    if _parser.translation_unit_dir:
        if not os.path.isdir(_parser.translation_unit_dir):
            os.makedirs(_parser.translation_unit_dir)
        # use ast file if translation_unit_dir not contain ast file
        _parser.ast_file = glob(os.path.join(_parser.translation_unit_dir, "*" + AST_EXT_FILE))
    else:
        # cannot clean ast file if no directory
        _parser.clean_ast = False

    # include files for clang
    if _parser.include_clang:
        _lst_include = [os.path.join(_root_dir, include) for include in _parser.include_clang.split(";")]
    else:
        _lst_include = []
    # validate if all path exist
    for include in _lst_include:
        if not os.path.exists(include):
            print("Warning, include '%s' not exist." % include)
    # find include directory
    if _parser.find_include:
        key = "include"
        lst_find = [os.path.join(dir_path, key) for dir_path, dir_names, _ in os.walk(_root_dir) if key in dir_names]
        _lst_include.extend(lst_find)

    # reorganize include argument for clang
    _parser.lst_include_clang = ["-I" + include for include in _lst_include]

    if _parser.debug and not _parser.quiet:
        # don't show files from parser
        print("Debug argument list - %s" % _parser)

    # fill files to parse
    if os.path.isdir(_parser.working_path):
        _lst_file = []
        for dir_path, _, _ in os.walk(_parser.working_path):
            for a in CPP_EXT_FILE:
                _lst_file.extend(glob(os.path.join(dir_path, a)))
    elif os.path.isfile(_parser.working_path):
        _lst_file = [_parser.working_path]
    else:
        raise Exception("Argument --working_path '%s' is not a file or a dir." % _parser.working_path)
    # remove root_directory from file, for better visibility and filter with exclude dir
    # TODO add ignore option from parsing
    # TODO fast fix to ignore gtest
    _pos_cut_path = len(_root_dir) + 1
    _parser.files = [_file[_pos_cut_path:] for _file in _lst_file if "/test/" not in _file and "/build/" not in _file]

    return _parser


class ClangParserGenerator:
    def __init__(self, _lst_file):
        self._lst_file = _lst_file

    def generator(self):
        for _file in self._lst_file:
            yield ast.clang_parser(_file)


def start_clang_process(_parser):
    if _parser.clean_ast:
        for _file in _parser.ast_file:
            os.remove(_file)
        _parser.ast_file = []

    lst_clang_parser_arg = [(f, _parser.root_directory, _parser.lst_include_clang, _parser) for f in _parser.files]

    if _parser.disable_threading:
        it = ClangParserGenerator(lst_clang_parser_arg).generator()
    else:
        it = Pool(processes=_parser.nb_cpu).imap_unordered(ast.clang_parser, lst_clang_parser_arg)

    # execute and return result for all file
    if _parser.quiet:
        lst_result = [clang_obj_result for clang_obj_result in it]
    else:
        i_file = 0
        count_file = len(lst_clang_parser_arg)
        lst_result = []
        for clang_obj_result in it:
            i_file += 1
            print("(%s/%s) File %s" % (i_file, count_file, clang_obj_result[0]))
            lst_result.append(clang_obj_result)
    # compute ast completion
    # clang_parser.class_completion(lst_result)
    return lst_result


if __name__ == '__main__':
    start_time = time.time()
    start_clock = time.clock()
    parser = validate_parser(parse_args())

    lst_obj_ast = start_clang_process(parser)

    if parser.generate_csv_stat:
        result.generate_stat_csv.GenerateStatCsv(parser, lst_obj_ast).generate_stat()

    if parser.generate_uml:
        result.generate_uml.GenerateUml(parser, lst_obj_ast).generate_uml()

    if parser.generate_control_flow:
        result.generate_cfg.GenerateCfg(parser, lst_obj_ast).generate_cfg()

    if parser.generate_dominator:
        result.generate_dominator.GenerateDominator(parser, lst_obj_ast).generate_dominator()
        result.generate_dominator.GenerateDominator(parser, lst_obj_ast, is_dominator=False).generate_dominator()

    duration_time = datetime.timedelta(seconds=time.time() - start_time)
    duration_clock = datetime.timedelta(seconds=time.clock() - start_clock)
    if not parser.quiet:
        print("Elapsed time was %s and elapsed clock was %s." % (duration_time, duration_clock))
