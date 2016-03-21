#!/usr/bin/env python2
# -*- coding: utf-8 -*-


class File(object):
    def __init__(self, file_location):
        if file_location:
            self.name = file_location.name
        else:
            self.name = ""

    def __repr__(self):
        return self.name


class Location(object):
    def __init__(self, location):
        if location:
            self.line = location.line
            self.column = location.column
            self.file = File(location.file)
        else:
            self.line = -1
            self.column = -1
            self.file = File(None)

    def __repr__(self):
        return "%s l %s c %s" % (self.file, self.line, self.column)
