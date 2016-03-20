#!/usr/bin/env python2
# -*- coding: utf-8 -*-


class File(object):
    def __init__(self, file_location):
        self.name = file_location.name


class Location(object):
    def __init__(self, location):
        self.line = location.line
        self.column = location.column
        self.file = File(location.file)
