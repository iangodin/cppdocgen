#!/usr/bin/env python3

import sys
import pathlib
import json
from comments import gather_comments, FakeCursor
from pprint import pprint, pformat
from clang.cindex import Index, Cursor, CursorKind, TokenKind, TranslationUnit, SourceLocation, SourceRange, FileInclusion, File
from decl_node import decl_node
from gather_decls import gather_decls

global path_cache
path_cache = {}

def path_from_location( location ):
    result = None
    if isinstance( location, SourceLocation ) and location.file:
        global path_cache
        filename = str( location.file.name )
        result = path_cache.get( filename, None )
        if result == None:
            result = pathlib.Path( filename ).resolve()
            path_cache[filename] = result
    return result

def get_file_extent( tu, filename ):
    def srcloc( size ):
        result = SourceLocation.from_offset( tu, filename, size )
        if str( result.file ) != str( filename ):
            result = None
        return result

    large = 1
    end = srcloc( large )
    while isinstance( end, SourceLocation ):
        large *= 2
        end = srcloc( large )
    small = large // 2
    while large - small > 1:
        mid = ( small + large ) // 2
        end = srcloc( mid )
        if isinstance( end, SourceLocation ):
            small = mid
        else:
            large = mid
    end = srcloc( small )
    start = srcloc( 0 )
    return SourceRange.from_locations( start, end )

def path_from_include( include ):
    result = None
    if isinstance( include, FileInclusion ) and include.include:
        global path_cache
        filename = str( include.include.name )
        result = path_cache.get( filename, None )
        if result == None:
            result = pathlib.Path( filename ).resolve()
            path_cache[filename] = result
    return result

def lex_parent_list( cursor ):
    result = []
    if not isinstance( cursor, Cursor ):
        return result
    if cursor.kind == CursorKind.TRANSLATION_UNIT:
        return []
    if isinstance( cursor.lexical_parent, Cursor ):
        result = lex_parent_list( cursor.lexical_parent )

    name = cursor.spelling
    if cursor.kind == CursorKind.CXX_ACCESS_SPEC_DECL:
        name = next( cursor.get_tokens() ).spelling
    elif cursor.kind == CursorKind.COMPOUND_STMT:
        name = '{}'
    result.append( ( cursor.kind.is_declaration(), name ) )
    return result

def lex_parent( cursor ):
    result = ''
    for p in lex_parent_list( cursor ):
        #if p[0] == False:
        #    break
        if len( result ) > 0:
            result = result + '::' + p[1]
        else:
            result = p[1]
    return result

decl_kinds = [
    CursorKind.NAMESPACE,
    CursorKind.CLASS_DECL,
    CursorKind.STRUCT_DECL,
    CursorKind.UNION_DECL,
    CursorKind.ENUM_DECL,
    CursorKind.COMPOUND_STMT,
    CursorKind.CXX_METHOD,
    CursorKind.CONSTRUCTOR,
    CursorKind.DESTRUCTOR,
    CursorKind.FIELD_DECL,
    CursorKind.PARM_DECL,
    CursorKind.ENUM_CONSTANT_DECL,
    CursorKind.FUNCTION_DECL,
    CursorKind.VAR_DECL,
    CursorKind.CXX_ACCESS_SPEC_DECL,
    CursorKind.TRANSLATION_UNIT,
]

decl_skip_children = [
    CursorKind.COMPOUND_STMT,
    CursorKind.VAR_DECL,
]

ignore_kinds = [
    CursorKind.TYPE_REF,
]

def create_decls( cursor, topfile, extent ):
    lst = []
    if cursor.location.file != None and str( cursor.location.file ) != topfile:
        return lst
    k = cursor.kind

    if k in decl_kinds:
        if k == CursorKind.TRANSLATION_UNIT:
            cursor = FakeCursor( cursor, extent )
        lst.append( cursor )
    elif k in ignore_kinds:
        pass
    else:
        print( "NOT A DECL?!? " + cursor.kind.name )

    if cursor.kind not in decl_skip_children:
        for c in cursor.get_children():
            lst += create_decls( c, topfile, extent )
    return lst

def create_comments( tokens, topfile ):
    comments = []
    for tok in tokens:
        if tok.kind == TokenKind.COMMENT:
            if tok.location.file != None and str( tok.location.file ) != topfile:
                continue
            comments.append( ( tok.spelling, tok.location.offset ) )
    return comments

# Check if a contains b
def range_contains( a, b ):
    if a[0] <= b[0] and a[1] >= b[1]:
        return True
    if a[1] < b[0]:
        return False
    if a[0] > b[1]:
        return False
    raise Exception( "overlapping ranges" )

def insert_decl_tree( cursor, lst ):
    inserted = False
    rng = ( cursor.extent.start.offset, cursor.extent.end.offset )
    for i in range( len( lst ) ):
        ( csr, children ) = lst[i]
        r = ( csr.extent.start.offset, csr.extent.end.offset )
        if range_contains( r, rng ):
            insert_decl_tree( cursor, children )
            inserted = True
        elif range_contains( rng, r ):
            tmp = ( cursor, [ lst[i] ] )
            lst[i] = tmp
            inserted = True
    if not inserted:
        lst.append( ( cursor, [] ) )

def create_decl_tree( decls ):
    lst = []
    for cursor in decls:
        insert_decl_tree( cursor, lst )
    return lst

def range_contains_loc( rng, loc ):
    if loc >= rng[0] and loc < rng[1]:
        return True
    return False

def find_following_decl( parent, decls, loc ):
    for ( cursor, children ) in decls:
        name = lex_parent( cursor )
        rng = ( cursor.extent.start.offset, cursor.extent.end.offset )
        if loc < rng[0]:
            return name
        elif loc < rng[1]:
            return find_following_decl( name, children, loc )
    return parent

def find_preceding_decl( parent, decls, loc ):
    for ( cursor, children ) in reversed( decls ):
        name = lex_parent( cursor )
        rng = ( cursor.extent.start.offset, cursor.extent.end.offset )
        if loc > rng[1]:
            return name
        elif loc > rng[0]:
            return find_preceding_decl( name, children, loc )
    return parent

def assign_comments( decls, comments ):
    result = {}
    top = decls[0][0]
    for ( cmt, loc ) in comments:
        if cmt.startswith( '//!<' ) or cmt.startswith( '///<' ) or cmt.startswith( '/*!<' ) or cmt.startswith( '/**<' ):
            decl = find_preceding_decl( top, decls, loc )
        else:
            decl = find_following_decl( top, decls, loc )
        lst = result.get( decl, [] )
        lst.append( cmt )
        result[decl] = lst
    return result

def merge( tree, comments ):
    for key in tree['key']:
        tree['comments'] += comments.get( key, [] )
    del tree['key']
    for c in tree['children']:
        merge( c, comments )

def main():
    from optparse import OptionParser, OptionGroup

    global opts

    parser = OptionParser("usage: %prog [options] {filename} [clang-args*]")
    parser.add_option("", "--dir", dest="dir",
                      help="Document files inside this directory",
                      metavar="N", type=str, default=".")
    parser.add_option("", "--pretty", dest="pretty",
                      help="Pretty print the output JSON",
                      default=False, action="store_true")
    parser.disable_interspersed_args()
    ( opts, args ) = parser.parse_args()

    if len(args) == 0:
        parser.error('invalid number arguments')

    filename, *clang_args = args
    topdir = pathlib.Path( opts.dir ).resolve()

    index = Index.create()
    tu = index.parse( filename, clang_args ) #, options=TranslationUnit.PARSE_SKIP_FUNCTION_BODIES)
    if not tu:
        raise Exception( "unable to load input" )

    for diag in tu.diagnostics:
        print( diag )
    print( '~~~~~~~~~~' )

    def dump_cursor( cursor, indent, force = False ):
        filepath = path_from_location( cursor.location )
        if not force:
            if filepath:
                if topdir not in filepath.parents:
                    return
            else:
                return
        tabs = '  ' * indent
        print( tabs + cursor.kind.name + ' ' + cursor.spelling + ' ' + str( cursor.extent.start.offset ) + ' - ' + str( cursor.extent.end.offset ) )
        if cursor.kind not in decl_skip_children:
            for c in cursor.get_children():
                dump_cursor( c, indent + 1 )
    #dump_cursor( tu.cursor, 0, True )

    files = [str( inc.include.name ) for inc in tu.get_includes() if topdir in path_from_include( inc ).parents]
    files.insert( 0, tu.spelling )

    cmts = gather_comments( tu, files )

    output = pathlib.Path( 'cppinfo.json' )

    with output.open( 'w' ) as f:
        if opts.pretty:
            f.write( json.dumps( cmts, indent=2 ) )
        else:
            f.write( json.dumps( cmts ) )

if __name__ == '__main__':
    main()

