#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from ast_object import ASTObject


class OperatorVariable(object):
    def __init__(self, lst_declare=[], lst_gen=[]):
        self.lst_declare = lst_declare
        self.lst_gen = lst_gen
        # self.lst_kill = lst_kill


class Variable(object):
    def __init__(self, stmt):
        super(Variable, self).__init__()
        self.stmt = stmt
