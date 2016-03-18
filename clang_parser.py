#!/usr/bin/env python2
# -*- coding: utf-8 -*-
import collections
import os
import sys
import uuid
import copy

AST_EXT_FILE = ".ast"

sys.path.append("/opt/llvm/tools/clang/bindings/python")
import clang.cindex

# clang.cindex.Config.set_library_path("/usr/lib/")
clang.cindex.Config.set_library_file("/opt/llvm/build/lib/libclang.so.3.7")
_clang_lib = clang.cindex.conf.lib

CLANG_DEFAULT_ARG = ['-x', 'c++', '-std=c++11', '-I/opt/llvm/build/lib/clang/3.7.1/include']


# dot function
def _get_dot_lst_cursor(lst_ast_obj, parent_ast_obj):
    char_new_line = "\\l"
    # example : "+ name : string\l+ age : int\l"
    # or empty : ""
    str_var = char_new_line.join([_get_dot_format(var, parent_ast_obj) for var in lst_ast_obj])
    if str_var:
        str_var += char_new_line
    return str_var


def _get_dot_format(ast_obj, parent_ast_obj=None):
    # example : "+ name : string"
    #
    # + Public
    # - Private
    # # Protected
    # ~ Package (default visibility)

    if ast_obj.access_specifier == clang.cindex.AccessSpecifier.PUBLIC:
        sign = "+ "
    elif ast_obj.access_specifier == clang.cindex.AccessSpecifier.PROTECTED:
        sign = "# "
    elif ast_obj.access_specifier == clang.cindex.AccessSpecifier.PRIVATE:
        sign = "- "
    elif ast_obj.access_specifier == clang.cindex.AccessSpecifier.NONE:
        sign = "~ "
    else:  # elif cursor.access_specifier == clang.cindex.AccessSpecifier.INVALID:
        print("Warning, receive AccessSpecifier.Invalid for %s obj, from : %s. File %s, mangled %s" % (
            ast_obj.name_tmpl, parent_ast_obj.name_tmpl if parent_ast_obj else None, ast_obj.file_name,
            ast_obj.mangled_name))
        sign = "? "

    return "%s %s : %s" % (sign, ast_obj.name_tmpl, ast_obj.type)


# end dot function


def get_tokens_statistic(cursor):
    # TODO to get else if, check if offset is inside of 5. c_child.location.offset
    lst_token_key = ["if", "else", "else if", "switch", "case", "while", "for", "break", "continue", "return", "using",
                     "try", "catch"]
    lst_token = [c_child.spelling for c_child in cursor.get_tokens() if
                 c_child.kind is clang.cindex.TokenKind.KEYWORD and c_child.spelling in lst_token_key]
    return collections.Counter(lst_token)


def _find_derived_class(cursor):
    # the cursor need to be a class
    # iterate in token
    # stop iteration when meet '{'
    # store class name after ':'
    # remove reserved word like public, private
    end_key = "{"
    begin_store_key = ":"
    new_class_key = ","
    begin_store = False
    reserved_word = ["public", "private"]
    lst_token = []
    word_completion = ""
    for token in cursor.get_tokens():
        word = token.spelling

        # end iterate condition
        if word == end_key:
            if word_completion:
                lst_token.append(word_completion)
            return lst_token

        # begin store condition
        if not begin_store:
            if word == begin_store_key:
                begin_store = True
            continue

        # another derived class
        if word == new_class_key:
            lst_token.append(word_completion)
            continue

        if word not in reserved_word:
            word_completion += word


def get_variables(cursor):
    lst_kind_var = [clang.cindex.CursorKind.VAR_DECL]
    return [Variable(c_child, c_child.location.file.name, store_variable=False) for c_child in cursor.walk_preorder() if
            c_child.kind in lst_kind_var]


def get_annotations(cursor):
    return [c_child.displayname for c_child in cursor.get_children()
            if c_child.kind == clang.cindex.CursorKind.ANNOTATE_ATTR]


class File(object):
    def __init__(self, file_location):
        self.name = file_location.name


class Location(object):
    def __init__(self, cursor):
        self.line = cursor.location.line
        self.column = cursor.location.column
        self.file = File(cursor.location.file)


class ASTObject(object):
    def __init__(self, cursor, filename=None, store_variable=True):
        # cursor information
        self.name = cursor.spelling
        self.name_tmpl = cursor.displayname
        self.location = Location(cursor)
        self._kind_id = cursor.kind.value
        self.mangled_name = cursor.mangled_name
        self._access_specifier = cursor.access_specifier.value
        self.type = cursor.type.spelling

        self.file_name = filename if filename else self.location.file.name
        # self.annotations = get_annotations(cursor)
        self.variable = get_variables(cursor) if store_variable else []
        self.count_variable = len(self.variable)
        self.keywords = None

    @property
    def kind(self):
        return clang.cindex.CursorKind.from_id(self._kind_id)

    @property
    def access_specifier(self):
        return clang.cindex.AccessSpecifier.from_id(self._access_specifier)


class Class(ASTObject):
    def __init__(self, cursor, filename=None):
        super(Class, self).__init__(cursor, filename=filename)

        self.methods = [Method(c_child, filename) for c_child in cursor.get_children() if
                        c_child.kind is clang.cindex.CursorKind.CXX_METHOD]

        self.derived_class = [Class(c_child) for c_child in cursor.get_children() if
                              c_child.kind is clang.cindex.CursorKind.CXX_BASE_SPECIFIER]

        self.namespace_name = cursor.type.spelling

    def __repr__(self):
        return self.to_string()

    def get_dot(self):
        # example : "{Animal|+ name : string\l+ age : int\l|+ die() : void\l}"
        # if self.derived_class:
        #     self.namespace_name += " - " + str(self.derived_class)
        msg = "{%s|%s|%s}" % (self.namespace_name,
                              _get_dot_lst_cursor(self.variable, self),
                              _get_dot_lst_cursor(self.methods, self))
        # need to remove bad character
        msg = msg.replace("<", "\\<")
        msg = msg.replace(">", "\\>")
        return msg

    def to_string(self):
        # TODO change this to_string. Move this into export.
        # file_str = "File %s\n" % self.file_name
        class_str = "\t+--%s - %s\n" % (self.kind, self.name_tmpl)
        method_str = "\n".join(["\t|\t+--%s - %s" % (clang.cindex.CursorKind.CXX_METHOD, f) for f in self.methods])
        # return file_str + class_str + method_str
        return class_str + method_str

    def merge_method(self, lst_method):
        i = len(lst_method)
        for method in reversed(lst_method):
            i -= 1
            if not isinstance(method, Function) and not isinstance(method, Method):
                continue
            j = 0
            for class_method in self.methods:
                if method.mangled_name == class_method.mangled_name:
                    self.methods[j] = method
                    del lst_method[i]
                j += 1


def has_return(lst_cursor):
    for c, lst in lst_cursor:
        if c.kind is clang.cindex.CursorKind.RETURN_STMT:
            return True
        if has_return(lst):
            return True
    return False


def get_stmt_name(kind):
    if kind is clang.cindex.CursorKind.COMPOUND_STMT:
        return "{...}"
    if kind is clang.cindex.CursorKind.CASE_STMT:
        return "case"
    if kind is clang.cindex.CursorKind.DEFAULT_STMT:
        return "default"
    if kind is clang.cindex.CursorKind.IF_STMT:
        return "if"
    if kind is clang.cindex.CursorKind.SWITCH_STMT:
        return "switch"
    if kind is clang.cindex.CursorKind.WHILE_STMT:
        return "while"
    if kind is clang.cindex.CursorKind.DO_STMT:
        return "do"
    if kind is clang.cindex.CursorKind.FOR_STMT:
        return "for"
    if kind is clang.cindex.CursorKind.GOTO_STMT:
        return "goto"
    if kind is clang.cindex.CursorKind.CONTINUE_STMT:
        return "continue"
    if kind is clang.cindex.CursorKind.BREAK_STMT:
        return "break"
    if kind is clang.cindex.CursorKind.RETURN_STMT:
        return "return"
    if kind is clang.cindex.CursorKind.CXX_CATCH_STMT:
        return "catch"
    if kind is clang.cindex.CursorKind.CXX_TRY_STMT:
        return "try"
    if kind is clang.cindex.CursorKind.CXX_FOR_RANGE_STMT:
        return "for"
    return "UNKNOWN"


class Function(ASTObject):
    def __init__(self, cursor, filename=None):
        # TODO keep a link to his parent
        super(Function, self).__init__(cursor, filename)
        self.keywords_stmt = get_tokens_statistic(cursor)
        self.keywords = self.keywords_stmt + collections.Counter(var=self.count_variable)
        self.is_valid_cfg = False
        self.enable_cfg = False
        if filename in cursor.location.file.name and not cursor.is_virtual_method():
            self.cfg = Function.find_control_flow(cursor)
            self.lst_cfg = collections.Counter()
            is_type_void = cursor.result_type.kind is clang.cindex.TypeKind.VOID
            self.print_control_flow(self.cfg, parent=cursor, is_type_void=is_type_void)
            self.validate_stmt()
            print("\n")
            self.enable_cfg = True
        else:
            self.cfg = []
            self.lst_cfg = []

    def get_dot(self):
        return _get_dot_format(self)

    def __repr__(self):
        return self.to_string()

    def to_string(self):
        # file_str = "File %s\n" % self.file_name
        if self.kind is clang.cindex.CursorKind.CXX_METHOD:
            function_str = "%s %s" % (self.name, self.keywords.items())
        else:
            function_str = "\t+--%s - %s %s" % (self.kind, self.name, self.keywords.items())
        # return file_str + function_str
        return function_str

    @staticmethod
    def find_control_flow(cursor):
        if not isinstance(cursor, clang.cindex.Cursor):
            return []

        filter_stmt = [clang.cindex.CursorKind.COMPOUND_STMT,
                       clang.cindex.CursorKind.CASE_STMT,
                       clang.cindex.CursorKind.DEFAULT_STMT,
                       clang.cindex.CursorKind.IF_STMT,
                       clang.cindex.CursorKind.SWITCH_STMT,
                       clang.cindex.CursorKind.WHILE_STMT,
                       clang.cindex.CursorKind.DO_STMT,
                       clang.cindex.CursorKind.FOR_STMT,
                       clang.cindex.CursorKind.GOTO_STMT,
                       clang.cindex.CursorKind.CONTINUE_STMT,
                       clang.cindex.CursorKind.BREAK_STMT,
                       clang.cindex.CursorKind.RETURN_STMT,
                       clang.cindex.CursorKind.CXX_CATCH_STMT,
                       clang.cindex.CursorKind.CXX_TRY_STMT,
                       clang.cindex.CursorKind.CXX_FOR_RANGE_STMT
                       ]
        function_stmt = [
            clang.cindex.CursorKind.COMPOUND_STMT
        ]

        def find_child_control_flow(stmt_cursor):
            l = []
            if not isinstance(stmt_cursor, clang.cindex.Cursor):
                return l

            for child in stmt_cursor.get_children():
                if child.kind in filter_stmt:
                    if child.kind in function_stmt:
                        return find_child_control_flow(child)
                    l.insert(0, (Statement(child), find_child_control_flow(child)))
            return l

        # find first compound of function and get child control flow
        start_stmt_cursor = [c for c in cursor.get_children() if c.kind in function_stmt]
        if start_stmt_cursor:
            return find_child_control_flow(start_stmt_cursor[0])
        return []

    def merge(self, fct):
        if not isinstance(fct, Function):
            return
        self.count_variable += fct.count_variable
        self.keywords += fct.keywords

    def print_control_flow(self, lst, no_iter=0, parent=None, is_type_void=False):
        i = 0
        if parent:
            print("file %s line %s mangled %s" % (parent.location.file.name, parent.location.line, parent.mangled_name))
            print("%s%s. %s - %s" % (no_iter * "\t", i, "Entry main", parent.displayname))

        for cursor, lst_child in lst:
            is_compound = cursor.kind is clang.cindex.CursorKind.COMPOUND_STMT
            i += 1
            location = cursor.location
            stmt_name = get_stmt_name(cursor.kind)
            print("%s%s. %s - line %s column %s" % (no_iter * "\t", i, stmt_name, location.line, location.column))
            if not is_compound:
                self.lst_cfg[stmt_name] += 1

            if lst_child:
                # c_no_inter = no_iter + 1 if not is_compound else no_iter
                c_no_inter = no_iter + 1
                self.print_control_flow(lst_child, no_iter=c_no_inter)
        if parent and lst:
            if not is_type_void and not has_return(lst):
                print("Error, missing return statement.")

    def validate_stmt(self):
        if not self.keywords_stmt:
            return
        if self.lst_cfg != self.keywords_stmt:
            print("ERROR, Count stmt keyword '%s' is different of cfg '%s'." % (self.keywords_stmt, self.lst_cfg))
            pass
        else:
            self.is_valid_cfg = True
            print("INFO, %s" % self.keywords_stmt)


class Method(Function):
    def __repr__(self):
        return self.to_string()

    def to_string(self):
        return "%s %s" % (self.name, self.keywords.items())


class Variable(ASTObject):
    def __init__(self, cursor, filename=None, store_variable=True):
        super(Variable, self).__init__(cursor, filename=filename, store_variable=store_variable)


class Statement(ASTObject):
    def __init__(self, cursor):
        super(Statement, self).__init__(cursor, filename=None, store_variable=False)
        self.name = get_stmt_name(cursor.kind)
        self.unique_name = uuid.uuid4()

    def label(self):
        return "%s\nline %s" % (self.name, self.location.line)

    def is_common_stmt(self):
        lst_clang_stmt = [
            clang.cindex.CursorKind.CASE_STMT,
            clang.cindex.CursorKind.DEFAULT_STMT,
            clang.cindex.CursorKind.IF_STMT,
            clang.cindex.CursorKind.SWITCH_STMT,
            clang.cindex.CursorKind.WHILE_STMT,
            clang.cindex.CursorKind.DO_STMT,
            clang.cindex.CursorKind.FOR_STMT,
            clang.cindex.CursorKind.GOTO_STMT,
            clang.cindex.CursorKind.CONTINUE_STMT,
            clang.cindex.CursorKind.BREAK_STMT,
            clang.cindex.CursorKind.RETURN_STMT,
            clang.cindex.CursorKind.CXX_CATCH_STMT,
            clang.cindex.CursorKind.CXX_TRY_STMT,
            clang.cindex.CursorKind.CXX_FOR_RANGE_STMT
        ]
        return self.kind in lst_clang_stmt

    def is_return(self):
        lst_clang_stmt = [
            clang.cindex.CursorKind.RETURN_STMT
        ]
        return self.kind in lst_clang_stmt

    def __repr__(self):
        return "\"%s\"" % self.name


def build_classes(cursor, filename, dir_name, _arg_parser, is_first_call=True):
    result = []
    # ignore Cursor Kind
    all_kind = [clang.cindex.CursorKind.CLASS_DECL, clang.cindex.CursorKind.CLASS_TEMPLATE,
                clang.cindex.CursorKind.NAMESPACE, clang.cindex.CursorKind.FUNCTION_TEMPLATE,
                clang.cindex.CursorKind.FUNCTION_DECL, clang.cindex.CursorKind.CXX_METHOD]

    # not work with .hh and .cc in same time
    header_filename = filename[filename.rfind("/"):-3]
    children_cursor = [m for m in cursor.get_children() if m.location.file and dir_name in m.location.file.name and
                       header_filename in m.location.file.name and m.kind in all_kind]

    # TODO merge when method is not in class, but in namespace
    for c_child in children_cursor:
        if c_child.kind in [clang.cindex.CursorKind.CLASS_DECL, clang.cindex.CursorKind.CLASS_TEMPLATE]:
            # eliminate forward declaration class, if token size <= 3
            if len([t for t in c_child.get_tokens()]) > 3:
                cls = Class(c_child, filename)
                result.append(cls)
        elif c_child.kind == clang.cindex.CursorKind.NAMESPACE:
            result.extend(build_classes(c_child, filename, dir_name, _arg_parser, is_first_call=False))
        elif c_child.kind in [clang.cindex.CursorKind.FUNCTION_TEMPLATE, clang.cindex.CursorKind.FUNCTION_DECL,
                              clang.cindex.CursorKind.CXX_METHOD]:
            fct = Function(c_child, filename)
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


#
#
# def class_completion(lst_ast_obj):
#     dct_cls = create_class_dict_from_lst_ast_obj(lst_ast_obj)
#
#     # loop in class and update reference
#     # update derived class
#     for ast_name, ast_cls in dct_cls.items():
#         for str_derived_cls in ast_cls.derived_class:
#             print(ast_cls.name)


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

    _ast_file_exist = False
    _ast_file_path = ""

    if _arg_parser.translation_unit_dir:
        _ast_file_path = os.path.join(_arg_parser.translation_unit_dir, _path_to_filename(_file_name) + AST_EXT_FILE)
        _ast_file_exist = os.path.isfile(_ast_file_path)

    absolute_file_path = os.path.join(_dir_name, _file_name)
    options = clang.cindex.TranslationUnit.PARSE_SKIP_FUNCTION_BODIES if _arg_parser.remove_token else 0
    options = clang.cindex.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD

    _obj_c_clang_index = _clang_lib.clang_createIndex(_arg_parser.exclude_decl_from_PCH,
                                                      _arg_parser.show_missing_header_file)
    _clang_index = clang.cindex.Index(_obj_c_clang_index)

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
