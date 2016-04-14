#!/usr/bin/env python2
# -*- coding: utf-8 -*-


class ControlDependency(object):
    def __init__(self, stmt):
        self.stmt = stmt
        # key is other edge, value is (common ancestral, CD path)
        self.s = {}

    def generate_control_dependency(self):
        # find s for every node
        lst_stmt = self.stmt.generator_child()

        for stmt in lst_stmt:
            stmt.control.find_s()

    def find_s(self):
        stmt = self.stmt
        if not stmt.before_stmt:
            return
        for last_stmt in [b for a in stmt.get_child(stmt.before_stmt) for b in list(a)]:
            # check not (y pdom x)
            stack_parent_last_stmt = last_stmt.get_dominator_parent_stack(last_stmt, ref_key="post_dominator")
            if stmt in stack_parent_last_stmt:
                continue

            # get first ancestral common
            common_stmt_ancestral = None
            stack_parent_stmt = stmt.get_dominator_parent_stack(stmt, ref_key="post_dominator")
            if last_stmt in stack_parent_stmt:
                common_stmt_ancestral = last_stmt
            else:
                # search common point
                for pdom_stmt in stack_parent_stmt[1:]:
                    for pdom_last_stmt in stack_parent_last_stmt[1:]:
                        if pdom_last_stmt == pdom_stmt:
                            common_stmt_ancestral = pdom_last_stmt
                            break
                    if common_stmt_ancestral:
                        break

            if common_stmt_ancestral is not None:
                # find CD path
                cd_path = []
                for pdom_stmt in stack_parent_stmt:
                    if pdom_stmt == common_stmt_ancestral:
                        break
                    cd_path.append(pdom_stmt)

                self.s[last_stmt] = (common_stmt_ancestral, cd_path)
            else:
                print("Error, cannot find ancestral common for node %s and %s." % (stmt, last_stmt))
