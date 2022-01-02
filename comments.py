#!/usr/bin/env python3

import pathlib
from pprint import pprint
from clang.cindex import Index, Cursor, CursorKind, TokenKind, TranslationUnit, SourceLocation, SourceRange, FileInclusion, File

Cursor.__hash__ = lambda c: c.hash

global path_cache
path_cache = {}

class FakeCursor:
    def __init__( self, cursor, extent ):
        self.kind = cursor.kind
        self.location = extent.start
        self.spelling = str( self.location.file.name )
        self.extent = extent
        self.cursor = cursor
        pass

    def get_children( self ):
        return self.cursor.get_children()

def get_diag_info(diag):
    return { 'severity' : diag.severity,
             'location' : diag.location,
             'spelling' : diag.spelling,
             'ranges' : diag.ranges,
             'fixits' : diag.fixits }

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

def sem_parent_list( cursor ):
    result = []
    if not isinstance( cursor, Cursor ):
        return result
    if cursor.kind == CursorKind.TRANSLATION_UNIT:
        return []
    if isinstance( cursor.semantic_parent, Cursor ):
        result = lex_parent_list( cursor.semantic_parent )

    name = cursor.spelling
    result.append( ( cursor.kind.is_declaration(), name ) )
    return result

def sem_parent( cursor ):
    result = ''
    for p in sem_parent_list( cursor ):
        if len( result ) > 0:
            result = result + '::' + p[1]
        else:
            result = p[1]
    return result

decl_kinds = [
    CursorKind.NAMESPACE,
    CursorKind.CLASS_DECL,
    CursorKind.CLASS_TEMPLATE,
    CursorKind.STRUCT_DECL,
    CursorKind.UNION_DECL,
    CursorKind.ENUM_DECL,
    CursorKind.COMPOUND_STMT,
    CursorKind.CXX_METHOD,
    CursorKind.CONSTRUCTOR,
    CursorKind.DESTRUCTOR,
    CursorKind.FIELD_DECL,
    CursorKind.PARM_DECL,
    CursorKind.TEMPLATE_TYPE_PARAMETER,
    CursorKind.ENUM_CONSTANT_DECL,
    CursorKind.FUNCTION_DECL,
    CursorKind.FUNCTION_TEMPLATE,
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
    CursorKind.NAMESPACE_REF,
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
        name = cursor
        rng = ( cursor.extent.start.offset, cursor.extent.end.offset )
        if loc < rng[0]:
            return name
        elif loc < rng[1]:
            return find_following_decl( name, children, loc )
    return parent

def find_preceding_decl( parent, decls, loc ):
    for ( cursor, children ) in reversed( decls ):
        name = cursor
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
        decl = top
        if cmt.startswith( '//!<' ) or cmt.startswith( '///<' ) or cmt.startswith( '/*!<' ) or cmt.startswith( '/**<' ):
            decl = find_preceding_decl( top, decls, loc )
        else:
            decl = find_following_decl( top, decls, loc )
        key = decl
        lst = result.get( key, [] )
        lst.append( cmt )
        result[key] = lst
    return result

def merge( master, more ):
    for ( name, comments ) in more.items():
        cmts = master.get( name, [] )
        cmts += comments
        master[name] = cmts

def dump_tree( tree, indent = 0 ):
    tabs = '  ' * indent
    for ( cursor, children ) in tree:
        ext = ( cursor.extent.start.offset, cursor.extent.end.offset )
        print( tabs + cursor.kind.name + ' ' + str( ext ) )
        dump_tree( children, indent + 1 )

def dump_decl( decl ):
    ext = ( decl.extent.start.offset, decl.extent.end.offset )
    pprint( ( decl.spelling, ext ) )

def gather_comments( tu, files ):
    cmts = {}
    for filename in files:
        file_extent = get_file_extent( tu, File.from_name( tu, filename ) )
        decl_list = create_decls( tu.cursor, filename, file_extent )
        #for item in decl_list:
        #    dump_decl( item )
        #print( '----------' )

        tokens = tu.get_tokens( extent = file_extent )
        comments = create_comments( tokens, filename )
        #for c in comments:
        #    pprint( c )
        #print( '----------' )

        tree = create_decl_tree( decl_list )
        #dump_tree( tree )
        #print( '----------' )

        result = assign_comments( tree, comments )

        merge( cmts, result )
    return cmts

