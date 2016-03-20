#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from clang_parser import clang


def merge_all_dicts(lst_dct):
    if not lst_dct:
        return {}
    first_dct = lst_dct[0]
    for dct in lst_dct[1:]:
        first_dct = merge_two_dicts(first_dct, dct)
    return first_dct


def merge_two_dicts(x, y):
    """Given two dicts, merge them into a new dict as a shallow copy."""
    z = x.copy()
    z.update(y)
    return z


dct_alias_operator_stmt = {
    clang.cindex.CursorKind.DECL_STMT: "declare",
    clang.cindex.CursorKind.BINARY_OPERATOR: "operator",
}

dct_alias_hide_child_stmt = {
    clang.cindex.CursorKind.DECL_STMT: "declare",
    clang.cindex.CursorKind.BINARY_OPERATOR: "operator",
    clang.cindex.CursorKind.RETURN_STMT: "return",
}

dct_alias_compound_stmt = {
    clang.cindex.CursorKind.COMPOUND_STMT: "{...}",
}

dct_alias_condition_stmt = {
    clang.cindex.CursorKind.CXX_FOR_RANGE_STMT: "for",
    clang.cindex.CursorKind.FOR_STMT: "for",
    clang.cindex.CursorKind.CASE_STMT: "case",
    clang.cindex.CursorKind.IF_STMT: "if",
    clang.cindex.CursorKind.WHILE_STMT: "while",
    clang.cindex.CursorKind.CXX_CATCH_STMT: "catch",
}

dct_alias_loop_stmt = {
    clang.cindex.CursorKind.CXX_FOR_RANGE_STMT: "for",
    clang.cindex.CursorKind.FOR_STMT: "for",
    clang.cindex.CursorKind.WHILE_STMT: "while",
    clang.cindex.CursorKind.DO_STMT: "do",
}

dct_alias_return_stmt = {
    clang.cindex.CursorKind.RETURN_STMT: "return",
}

dct_alias_affected_break_stmt = {
    clang.cindex.CursorKind.SWITCH_STMT: "switch",
    clang.cindex.CursorKind.DO_STMT: "do",
    clang.cindex.CursorKind.CXX_FOR_RANGE_STMT: "for",
    clang.cindex.CursorKind.FOR_STMT: "for",
    clang.cindex.CursorKind.WHILE_STMT: "while",
}

dct_alias_break_stmt = {
    clang.cindex.CursorKind.BREAK_STMT: "break",
}

dct_alias_continue_stmt = {
    clang.cindex.CursorKind.CONTINUE_STMT: "continue",
}

dct_alias_block_stmt = {
    clang.cindex.CursorKind.CASE_STMT: "case",
    clang.cindex.CursorKind.DEFAULT_STMT: "default",
    clang.cindex.CursorKind.SWITCH_STMT: "switch",
    clang.cindex.CursorKind.DO_STMT: "do",
    clang.cindex.CursorKind.CXX_TRY_STMT: "try",
    clang.cindex.CursorKind.CXX_FOR_RANGE_STMT: "for",
    clang.cindex.CursorKind.FOR_STMT: "for",
    clang.cindex.CursorKind.WHILE_STMT: "while",
    clang.cindex.CursorKind.IF_STMT: "if",
}

dct_alias_directive_stmt = {
    clang.cindex.CursorKind.DEFAULT_STMT: "default",
    clang.cindex.CursorKind.SWITCH_STMT: "switch",
    clang.cindex.CursorKind.DO_STMT: "do",
    clang.cindex.CursorKind.GOTO_STMT: "goto",
    clang.cindex.CursorKind.CONTINUE_STMT: "continue",
    clang.cindex.CursorKind.BREAK_STMT: "break",
    clang.cindex.CursorKind.RETURN_STMT: "return",
    clang.cindex.CursorKind.CXX_TRY_STMT: "try",
}

dct_alias_common_stmt = merge_two_dicts(dct_alias_condition_stmt, dct_alias_directive_stmt)

lst_alias_dct = [dct_alias_operator_stmt, dct_alias_directive_stmt, dct_alias_compound_stmt, dct_alias_condition_stmt]
dct_alias_stmt = merge_all_dicts(lst_alias_dct)
