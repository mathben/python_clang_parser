#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
from glob import glob
import argparse
import time
import datetime
from multiprocessing import Pool

import clang_parser
import export


def parse_args():
    _arg_parser = argparse.ArgumentParser(description="Python clang analyser c++")

    _arg_parser.add_argument('-d', '--debug', default=False, help='Enable debug', action='store_true')

    group = _arg_parser.add_argument_group("Parallelism")
    group.add_argument('--disable_threading', default=False, action='store_true',
                       help='Disable multi-process execution.')
    group.add_argument('-i', '--nb_cpu', default=None, type=int,
                       help='Default value is max cpu. Specify the count cpu usage.')

    group = _arg_parser.add_argument_group("Compilation")
    group.add_argument('-I', '--include_clang',
                       help='Add include file or directory. Separate each with \';\'.'
                            'Include can be absolute or relative from root_directory.')
    group.add_argument('--find_include', default=False, action='store_true',
                       help='If active, search include file in root_directory.')

    group = _arg_parser.add_argument_group("Configuration")
    group.add_argument('--root_directory', required=True,
                       help='Path of root directory. This path is use to filter files from '
                            'this directory only and set the working_path is not specified.')
    group.add_argument('--working_path',
                       help='Specify path of file or directory. Need to exist into root_directory.\n'
                            'If not specified, working_path will be root_directory.')

    return _arg_parser.parse_args()


def validate_parser(_parser):
    # validate argument
    # root directory
    if not os.path.isdir(_parser.root_directory):
        _parser.format_help()
        raise ValueError("--root_directory '%s' is not a valid directory" % _parser.root_directory)

    # force to clean path, like remove last /
    _root_dir = _parser.root_directory = os.path.abspath(_parser.root_directory)

    # working path
    if not _parser.working_path:
        _parser.working_path = _root_dir
    elif _root_dir in _parser.working_path:
        if not os.path.exists(_parser.working_path):
            _parser.format_help()
            raise ValueError("--working_path '%s' is not a valid directory or file." % _parser.working_path)
    else:
        new_path = os.path.abspath(os.path.join(_root_dir, _parser.working_path))
        if os.path.exists(new_path):
            _parser.working_path = new_path
        else:
            val = _parser.working_path, _root_dir
            raise ValueError("--working_path '%s' not exist in root_directory '%s'." % val)

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
        lst_find = [os.path.join(dirpath, key) for dirpath, dirnames, _ in os.walk(_root_dir) if key in dirnames]
        _lst_include.extend(lst_find)

    # reorganize include argument for clang
    _parser.lst_include_clang = ["-I" + include for include in _lst_include]

    if _parser.debug:
        # don't show files from parser
        print("Debug argument list - %s" % _parser)

    # search all file
    _lst_file = []
    if os.path.isdir(_parser.working_path):
        # pattern = ("*.cc", "*.cpp", "*.c")
        pattern = ("*.cc", "*.cpp")
        for dirpath, _, _ in os.walk(_parser.working_path):
            [_lst_file.extend(glob(os.path.join(dirpath, a))) for a in pattern]
        # remove root_directory from file
        _lst_file = [_file[len(_root_dir) + 1:] for _file in _lst_file]
    elif os.path.isfile(_parser.working_path):
        _lst_file.append(_parser.working_path)
    else:
        raise Exception("Argument --working_path '%s' is not a file or a dir." % _parser.working_path)

    _parser.files = _lst_file

    return _parser


class ClangParserGenerator:
    def __init__(self, _lst_file):
        self._lst_file = _lst_file

    def generator(self):
        for _file in self._lst_file:
            yield clang_parser.clang_parser(_file)


if __name__ == '__main__':
    start_time = time.time()
    start_clock = time.clock()
    parser = validate_parser(parse_args())

    csv_cursor_kind = [clang_parser.clang.cindex.CursorKind.CLASS_DECL,
                       clang_parser.clang.cindex.CursorKind.CLASS_TEMPLATE,
                       clang_parser.clang.cindex.CursorKind.CXX_METHOD,
                       clang_parser.clang.cindex.CursorKind.FUNCTION_TEMPLATE,
                       clang_parser.clang.cindex.CursorKind.FUNCTION_DECL]
    lst_result = []

    # TODO add ignore option from parsing
    # TODO fast fix to ignore gtest
    lst_file = [(f, parser.root_directory, parser.lst_include_clang) for f in parser.files if
                "/test/" not in f and "/build/" not in f]
    if parser.disable_threading:
        it = ClangParserGenerator(lst_file).generator()
    else:
        it = Pool(processes=parser.nb_cpu).imap_unordered(clang_parser.clang_parser, lst_file)

    count_file = len(lst_file)
    i_file = 0
    for t in it:
        i_file += 1
        if parser.debug:
            print("%s/%s File %s" % (i_file, count_file, t[0]))

        for c in t[2]:
            if parser.debug:
                print(c.to_string())

            if c.kind in csv_cursor_kind:
                lst_result.append(c)

        if parser.debug:
            print  # beautiful end line!

    duration_time = datetime.timedelta(seconds=time.time() - start_time)
    duration_clock = datetime.timedelta(seconds=time.clock() - start_clock)
    print("Elapsed time was %s and elapsed clock was %s." % (duration_time, duration_clock))

    export.create_csv(lst_result)
