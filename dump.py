#!/usr/bin/env python

#===- cindex-dump.py - cindex/Python Source Dump -------------*- python -*--===#
#
# Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
#===------------------------------------------------------------------------===#

from pprint import pprint
from clang.cindex import Index, CursorKind, TokenKind

"""
A simple command line tool for dumping a source file using the Clang Index
Library.
"""

def get_diag_info(diag):
    return { 'severity' : diag.severity,
             'location' : diag.location,
             'spelling' : diag.spelling,
             'ranges' : diag.ranges,
             'fixits' : diag.fixits }

def get_type( ty ):
    return ty.spelling

def get_cursor_id(cursor, cursor_list = []):
    if not opts.showIDs:
        return None

    if cursor is None:
        return None

    # FIXME: This is really slow. It would be nice if the index API exposed
    # something that let us hash cursors.
    for i,c in enumerate(cursor_list):
        if cursor == c:
            return i
    cursor_list.append(cursor)
    return len(cursor_list) - 1

def get_info(node, depth=0):
    semp = node.semantic_parent
    if semp:
        semp = semp.spelling
    else:
        semp = ''
    lexp = node.lexical_parent
    if lexp:
        lexp = lexp.spelling
    else:
        lexp = ''
    toks = [t.spelling for t in node.get_tokens()]
    if opts.maxDepth is not None and depth >= opts.maxDepth:
        children = None
    else:
        children = [get_info(c, depth+1)
                    for c in node.get_children()]
    result = { 'id' : get_cursor_id(node),
             'kind' : node.kind.name,
             'toks' : str( ' '.join( [tok.spelling for tok in node.get_tokens() if tok.kind != TokenKind.COMMENT ] ) ),
             #'usr' : str( node.get_usr() ),
             'spelling' : node.spelling,
             'displayname' : node.displayname,
             'comments' : node.brief_comment,
             'sem_parent' : semp,
             'lex_parent' : lexp,
             #'location' : str( node.location ),
             #'extent.start' : str( node.extent.start ),
             #'extent.end' : str( node.extent.end ),
             'is_definition' : node.is_definition(),
             #'tokens': toks,
             #'storage_class': str( node.storage_class ),
             #'linkage': str( node.linkage ),
             #'access_specifier': str( node.access_specifier ),
             'children' : children }
    if node.type:
        result['type'] = str( node.type.spelling )
    if node.result_type:
        result['result_type'] = get_type( node.result_type )
    return result

def main():
    from pprint import pprint
    import yaml

    from optparse import OptionParser, OptionGroup

    global opts

    parser = OptionParser("usage: %prog [options] {filename} [clang-args*]")
    parser.add_option("", "--show-ids", dest="showIDs",
                      help="Compute cursor IDs (very slow)",
                      action="store_true", default=False)
    parser.add_option("", "--max-depth", dest="maxDepth",
                      help="Limit cursor expansion to depth N",
                      metavar="N", type=int, default=None)
    parser.disable_interspersed_args()
    (opts, args) = parser.parse_args()

    if len(args) == 0:
        parser.error('invalid number arguments')

    index = Index.create()
    tu = index.parse(None, args)
    if not tu:
        parser.error("unable to load input")

    pprint(('diags', [get_diag_info(d) for d in  tu.diagnostics]))

    for tok in tu.cursor.get_tokens():
        if tok.spelling == 'inline':
            print( yaml.dump( get_info(tok.cursor), sort_keys=False ) )

    print( yaml.dump( get_info(tu.cursor), sort_keys=False ) )

    #tmp = next( tu.cursor.get_children() )
    #print( tmp.raw_comment )

if __name__ == '__main__':
    main()

