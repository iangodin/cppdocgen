#!/usr/bin/env python3

import pathlib
from pprint import pprint
from decl_node import sem_parent_list, decl_node
from clang.cindex import Index, Cursor, CursorKind, TokenKind, TranslationUnit, SourceLocation, SourceRange, FileInclusion, File, Token, AccessSpecifier

Cursor.__hash__ = lambda c: c.hash

global path_cache
path_cache = {}

class FakeToken:
    def __init__( self, spelling, parent, extent ):
        self.kind = TokenKind.COMMENT
        self.sem_parent = parent
        self.spelling = spelling
        self.displayname = spelling
        self.extent = extent
        self.canonical = self
        self.type = None
        self.result_type = None
        self.access_specifier = AccessSpecifier.INVALID

    def __hash__( self ):
        return hash( self.spelling )

    def get_tokens( self ):
        return []

class FakeCursor:
    def __init__( self, cursor, extent ):
        self.kind = cursor.kind
        self.location = extent.start
        self.spelling = str( self.location.file.name )
        self.extent = extent
        self.cursor = cursor
        self.canonical = cursor.canonical
        pass

    def get_children( self ):
        return self.cursor.get_children()

    def get_tokens( self ):
        return [ FakeToken( self.spelling, self, self.extent ) ]

def sem_parent( cursor ):
    if isinstance( cursor, FakeToken ):
        return sem_parent( cursor.sem_parent )
    else:
        if cursor.kind == CursorKind.TRANSLATION_UNIT:
            return ''
        else:
            return '::' + '::'.join( sem_parent_list( cursor )[:-1] )

kind_sep = {
    CursorKind.TEMPLATE_TYPE_PARAMETER: '<>',
    CursorKind.TEMPLATE_NON_TYPE_PARAMETER: '<>',
    CursorKind.PARM_DECL: '()',
}

def sem_name( cursor ):
    if isinstance( cursor, FakeToken ):
        return sem_name( cursor.sem_parent ) + '!!' + cursor.spelling
    elif isinstance( cursor, Cursor ) or isinstance( cursor, FakeCursor ):
        if cursor.kind == CursorKind.TRANSLATION_UNIT:
            return ''
        else:
            sep = kind_sep.get( cursor.kind, '::' )
            return sem_name( cursor.semantic_parent ) + sep + cursor.spelling
    else:
        assert not cursor, 'unknown cursor type ' + str( type( cursor ) )
        return ''


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

decl_kinds = [
    CursorKind.NAMESPACE,
    CursorKind.CLASS_DECL,
    CursorKind.CLASS_TEMPLATE,
    CursorKind.STRUCT_DECL,
    CursorKind.UNION_DECL,
    CursorKind.ENUM_DECL,
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
    CursorKind.TEMPLATE_REF,
    CursorKind.TYPE_REF,
    CursorKind.NAMESPACE_REF,
    CursorKind.COMPOUND_STMT,
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

def group_name( comment ):
    lines = comment[5:].strip().splitlines()
    return ( lines[0], lines[1:] )

def create_comments( tokens, topfile ):
    comments = []
    groups = []
    for tok in tokens:
        if tok.kind == TokenKind.COMMENT:
            if tok.location.file != None and str( tok.location.file ) != topfile:
                continue
            if tok.spelling.startswith( '///!!' ) or tok.spelling.startswith( '/**!!' ):
                ( name, cmts ) = group_name( tok.spelling )
                groups.append( FakeToken( name, None, tok.extent ) )
                if len( cmts ) > 0:
                    comments.append( ( '\n'.join( cmts ), tok.location.offset ) )
            else:
                comments.append( ( tok.spelling, tok.location.offset ) )
    return ( comments, groups )

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
        lst.sort( key=lambda t: t[0].extent.start.offset )

def assign_parent_to_groups( tree, parent ):
    for ( cursor, children ) in tree:
        assign_parent_to_groups( children, cursor )
        if isinstance( cursor, FakeToken ):
            print( cursor.spelling, " -> ", parent.spelling )
            cursor.sem_parent = parent.canonical

def create_decl_tree( decls ):
    lst = []
    for cursor in decls:
        insert_decl_tree( cursor, lst )
    assign_parent_to_groups( lst, None )
    return lst

def insert_groups( tree, groups ):
    for group in groups:
        insert_decl_tree( group, tree )

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

def gather_parents( tree, parents = {}, parent = '' ):
    group = None
    for ( cursor, children ) in tree:
        if group:
            parents[cursor.canonical] = group
        else:
            parents[cursor.canonical] = parent
        if isinstance( cursor, FakeToken ):
            group = parent + '!!' + cursor.spelling
        if cursor.kind == CursorKind.TRANSLATION_UNIT:
            gather_parents( children, parents, '' )
        else:
            gather_parents( children, parents, parent + '::' + cursor.spelling )
    return parents

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
    pprint( ( sem_name( decl ), ext ) )

def gather_comments( tu, files ):
    decl_cmts_list = {}
    parents = {}
    for filename in files:
        file_extent = get_file_extent( tu, File.from_name( tu, filename ) )

        # decl_list is a list of pairs ( cursor, extent )
        # extent is a pair of numbers ( start offset, end offset )
        decl_list = create_decls( tu.cursor, filename, file_extent )
        #print( "DECL_LIST" )
        #for item in decl_list:
        #    dump_decl( item )
        #print( '----------' )

        # Comments is a list of pairs ( comment, location )
        # location is an integer offset.
        # Groups is a list of group comments (FakeTokens)
        tokens = tu.get_tokens( extent = file_extent )
        ( comments, groups ) = create_comments( tokens, filename )
        #print( "COMMENTS" )
        #for c in comments:
        #    pprint( c )
        #print( '----------' )
        #print( "GROUPS" )
        #for g in groups:
        #    pprint( g )
        #print( '----------' )

        # Group comments are added to the decl_list.
        # That way, groups can have comments just like declarations.
        for g in groups:
            decl_list.append( g )
        #print( "DECL_LIST + GROUPS" )
        #for item in decl_list:
        #    dump_decl( item )
        #print( '----------' )

        # Create a tree of declarations (including groups).
        # The tree is created from the extents of each declaration/group.
        tree = create_decl_tree( decl_list )
        #print( "DECL_TREE" )
        #dump_tree( tree )
        #print( '----------' )

        # Assign comments to declarations
        # This is done based on the extent of the decls/groups and the location of comments.
        # decl_cmts is a dictionary of cursor/token -> list of comments
        # A cursor means a declaration, a token for groups.
        decl_cmts = assign_comments( tree, comments )
        #print( "DECL_CMTS" )
        #for item in decl_cmts.items():
        #    pprint( item )
        #print( '----------' )

        # Dictionary of node -> parent
        parents = parents | gather_parents( tree )
        #print( 'PARENTS' )
        #for ( node, parent ) in parents.items():
        #    pprint( ( node.spelling, parent ) )
        #print( '----------' )

        # Added any missing declarations with empty comment list.
        # This way all declarations will be present, even if they are not commented.
        for d in decl_list:
            if d not in decl_cmts:
                decl_cmts[d] = []

        # Finally add all of the decl_cmts into the final list
        for ( cursor, comments ) in decl_cmts.items():
            assert cursor.canonical, "missing canonical " + str( cursor )
            canon = cursor.canonical
            name = sem_name( canon )
            if canon.kind != CursorKind.TRANSLATION_UNIT:
                if canon not in decl_cmts_list:
                    node = decl_node( canon )
                    node['parent'] = sem_name( canon.semantic_parent )
                    decl_cmts_list[name] = node
                decl_cmts_list[name]['comments'] += comments

    print( "DECL_CMTS_LIST" )
    for item in decl_cmts_list.items():
        pprint( item, sort_dicts=False )
    print( '----------' )

    return decl_cmts_list

