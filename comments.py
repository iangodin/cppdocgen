#! /usr/bin/env python3

import pathlib
import re
import copy
from pprint import pprint
from decl_node import decl_node, decl_location
from node_type import cursor_to_type
from clang.cindex import Index, Cursor, CursorKind, TokenKind, TranslationUnit, SourceLocation, SourceRange, FileInclusion, File, Token, AccessSpecifier

Cursor.__hash__ = lambda c: c.hash

global path_cache
path_cache = {}

class FakeToken:
    def __init__( self, spelling, parent, extent ):
        self.kind = TokenKind.COMMENT
        self.semantic_parent = parent
        self.spelling = spelling
        self.displayname = spelling
        self.location = extent.start
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
    def __init__( self, cursor, extent, semparent = None ):
        self.kind = cursor.kind
        self.location = extent.start
        self.spelling = str( self.location.file.name )
        self.displayname = self.spelling
        self.extent = extent
        self.cursor = cursor
        self.type = cursor.type
        self.result_type = cursor.result_type
        self.canonical = cursor.canonical
        self.semantic_parent = semparent if semparent else cursor.semantic_parent
        self.access_specifier = AccessSpecifier.INVALID
        pass

    def get_children( self ):
        return self.cursor.get_children()

    def get_tokens( self ):
        return [ FakeToken( self.spelling, self, self.extent ) ]

fragment_kind = [ 'group', 'variable', 'function', 'param', 'tparam', 'field', 'method', 'constructor', 'destructor', 'friend' ]

def self_name( cursor ):
    if cursor.kind == CursorKind.TRANSLATION_UNIT:
        return ''
    elif cursor.kind == CursorKind.FRIEND_DECL:
        return self_name( next( cursor.get_children() ) )
    elif cursor.kind == CursorKind.CXX_ACCESS_SPEC_DECL:
        a = cursor.access_specifier
        if a == AccessSpecifier.PUBLIC:
            return 'Public'
        if a == AccessSpecifier.PROTECTED:
            return 'Protected'
        if a == AccessSpecifier.PRIVATE:
            return 'Private'
        return 'unknown'
    else:
        return cursor.spelling

def link_url( parent, node ):
    if node['kind'] == 'global':
        return '/index'
    else:
        parent = parent.split( '#', 1 )[0]
        sep = '/' if node['kind'] not in fragment_kind else '#'
        if sep == '/' and parent == '/index':
            parent = '/global'
        result = parent + sep + node['name']
        return result

def sem_name( cursor ):
    if isinstance( cursor, FakeToken ) or isinstance( cursor, Cursor ) or isinstance( cursor, FakeCursor ):
        if cursor.kind == CursorKind.TRANSLATION_UNIT:
            return ''
        else:
            parent = sem_name( cursor.semantic_parent )
            return parent + '/' + self_name( cursor )
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
    CursorKind.TEMPLATE_NON_TYPE_PARAMETER,
    CursorKind.ENUM_CONSTANT_DECL,
    CursorKind.TYPE_ALIAS_DECL,
    CursorKind.FRIEND_DECL,
    CursorKind.FUNCTION_DECL,
    CursorKind.FUNCTION_TEMPLATE,
    CursorKind.VAR_DECL,
    CursorKind.CXX_ACCESS_SPEC_DECL,
    CursorKind.TRANSLATION_UNIT,
]

decl_skip_children = [
    CursorKind.FRIEND_DECL,
    CursorKind.COMPOUND_STMT,
    CursorKind.VAR_DECL,
]

ignore_kinds = [
    CursorKind.OVERLOADED_DECL_REF,
    CursorKind.MEMBER_REF,
    CursorKind.TEMPLATE_REF,
    CursorKind.TYPE_REF,
    CursorKind.NAMESPACE_REF,
    CursorKind.COMPOUND_STMT,
    CursorKind.CXX_OVERRIDE_ATTR,
]

def create_decls( cursor, topfile, extent, parent = None ):
    lst = []
    if cursor.location.file != None and str( cursor.location.file ) != topfile:
        return lst
    k = cursor.kind

    if k in decl_kinds:
        if k == CursorKind.TRANSLATION_UNIT:
            cursor = FakeCursor( cursor, extent )
        elif k == CursorKind.TEMPLATE_TYPE_PARAMETER and k == CursorKind.TEMPLATE_NON_TYPE_PARAMETER and cursor.semantic_parent.kind == CursorKind.TRANSLATION_UNIT:
            cursor = FakeCursor( cursor, extent, parent )
        lst.append( cursor )
    elif k in ignore_kinds:
        pass
    elif k.is_expression():
        pass
    else:
        print( "UNKNOWN KIND: " + cursor.kind.name + ' (' + ' '.join( [x.spelling for x in cursor.get_tokens()] ) + ')' )

    if cursor.kind not in decl_skip_children:
        for c in cursor.get_children():
            lst += create_decls( c, topfile, extent, cursor )
    return lst

c_comment_start = re.compile( r'/[*]+([!]?[!<]?)(.*)' )
c_comment_cont = re.compile( r'[\s]*[*](.*)' )
cpp_comment = re.compile( r'//[/]*([!]?[!<]?)(.*)' )

def clean_c_comment( comment ):
    lines = comment.splitlines()
    lines[-1] = lines[-1][:-2] # Remove the ending */
    tag = ''
    for ( i, line ) in enumerate( lines ):
        if i == 0:
            match = c_comment_start.match( line )
            if match:
                tag = match.group( 1 )
                line = match.group( 2 )
            else:
                assert False, 'unknown C comment: ' + line
        else:
            match = c_comment_cont.match( line )
            if match:
                line = match.group( 1 )
        lines[i] = line
    return ( tag, lines )

def clean_cpp_comment( comment ):
    match = cpp_comment.match( comment )
    assert match, 'unknown C++ comment: ' + line
    tag = match.group( 1 )
    comment = match.group( 2 )
    return ( tag, [ comment ] )

def cleanup_comment( comment ):
    if comment.startswith( r'//' ):
        return clean_cpp_comment( comment )
    else:
        return clean_c_comment( comment )
    

def group_name( line ):
    name = line.strip()
    return name

def create_comments( tokens, topfile ):
    comments = []
    groups = []
    for tok in tokens:
        if tok.kind == TokenKind.COMMENT:
            if tok.location.file != None and str( tok.location.file ) != topfile:
                continue
            tag, cmts = cleanup_comment( tok.spelling )
            if tag == '!!':
                name = group_name( cmts[0] )
                groups.append( FakeToken( name, None, tok.extent ) )
                if len( cmts ) > 1:
                    comments.append( ( '!<', '\n'.join( cmts[1:] ), tok.location.offset ) )
            else:
                comments.append( ( tag, '\n'.join( cmts ), tok.location.offset ) )
    return ( comments, groups )

# Check if a contains b
def range_contains( a, b ):
    if a[0] <= b[0] and a[1] >= b[1]:
        return True
    if b[0] <= a[0] and b[1] >= a[1]:
        return False
    if a[1] < b[0] or a[0] > b[1]:
        return False
    raise Exception( "overlapping ranges " + str( a ) + ' ' + str( b ) )

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
            cursor.semantic_parent = parent.canonical

def create_decl_tree( decls ):
    lst = []
    for cursor in decls:
        insert_decl_tree( cursor, lst )
    assign_parent_to_groups( lst, None )
    return lst

def cleanup_groups( group ):
    new_group = []
    name_lookup = {}
    for ( cursor, children ) in group:
        name = self_name( cursor )
        kids = name_lookup.get( name, None )
        if kids != None:
            kids += children
        else:
            name_lookup[name] = children
            new_group.append( ( cursor, children ) )
    return new_group

def group_namespace( decls, parent ):
    namegroup = []
    typegroup = []
    funcgroup = []
    vargroup = []
    othergroup = []
    group = None
    group_cursor = None

    newchildren = []

    for ( cursor, children ) in decls:
        ty = cursor_to_type( cursor )
        if group != None and ty != 'group':
            group.append( ( cursor, group_childrens( children, cursor ) ) )
        elif ty in [ 'namespace' ]:
            namegroup.append( ( cursor, group_childrens( children, cursor ) ) )
        elif ty in [ 'class', 'struct', 'typedef' ]:
            typegroup.append( ( cursor, group_childrens( children, cursor ) ) )
        elif ty == 'function':
            funcgroup.append( ( cursor, group_childrens( children, cursor ) ) )
        elif ty == 'variable':
            vargroup.append( ( cursor, group_childrens( children, cursor ) ) )
        elif ty == 'group':
            if group:
                newchildren.append( ( group_cursor, group ) )
            group = []
            group_cursor = cursor
        else:
            othergroup.append( ( cursor, group_childrens( children, cursor ) ) )

    if group:
        newchildren.append( ( group_cursor, group ) )

    def add( group, name ):
        if group:
            start = min( [ x[0].extent.start for x in group ], key = lambda x: x.offset  )
            end = max( [ x[0].extent.end for x in group ], key = lambda x: x.offset )
            extent = SourceRange.from_locations( start, end )
            newchildren.append( ( FakeToken( name, cursor, extent ), group ) )

    add( namegroup, 'Namespace' )
    add( typegroup, 'Types' )
    add( funcgroup, 'Functions' )
    add( vargroup, 'Variables' )
    add( othergroup, 'Others' )
    return cleanup_groups( newchildren )

def group_class( decls, parent ):
    templategroup = []
    constructorgroup = []
    destructorgroup = []
    methodgroup = []
    fieldgroup = []
    typegroup = []
    othergroup = []
    group = None
    group_cursor = None

    newchildren = []

    for ( cursor, children ) in decls:
        ty = cursor_to_type( cursor )
        if group != None and ty != 'group':
            group.append( ( cursor, group_childrens( children, cursor ) ) )
        elif ty == 'tparam':
            templategroup.append( ( cursor, group_childrens( children, cursor ) ) )
        elif ty == 'constructor':
            constructorgroup.append( ( cursor, group_childrens( children, cursor ) ) )
        elif ty == 'destructor':
            destructorgroup.append( ( cursor, group_childrens( children, cursor ) ) )
        elif ty == 'method':
            methodgroup.append( ( cursor, group_childrens( children, cursor ) ) )
        elif ty == 'field':
            fieldgroup.append( ( cursor, group_childrens( children, cursor ) ) )
        elif ty in [ 'class', 'struct', 'typedef' ]:
            typegroup.append( ( cursor, group_childrens( children, cursor ) ) )
        elif ty == 'group':
            if group:
                newchildren.append( ( group_cursor, group ) )
            group = []
            group_cursor = cursor
        elif ty == 'access':
            if group:
                newchildren.append( ( group_cursor, group ) )
            group = []
            group_cursor = cursor
        else:
            othergroup.append( ( cursor, group_childrens( children, cursor ) ) )

    if group:
        newchildren.append( ( group_cursor, group ) )

    def add( group, name ):
        if group:
            start = min( [ x[0].extent.start for x in group ], key = lambda x: x.offset  )
            end = max( [ x[0].extent.end for x in group ], key = lambda x: x.offset )
            extent = SourceRange.from_locations( start, end )
            newchildren.append( ( FakeToken( name, cursor, extent ), group ) )

    add( typegroup, 'Types' )
    add( templategroup, 'Template Parameters' )
    add( constructorgroup, 'Constructors' )
    add( destructorgroup, 'Destructors' )
    add( methodgroup, 'Methods' )
    add( fieldgroup, 'Fields' )
    add( othergroup, 'Others' )

    return cleanup_groups( newchildren )

def group_other( decls, parent ):
    newchildren = []
    for ( cursor, children ) in decls:
        newchildren.append( ( cursor, group_childrens( children, cursor ) ) )
    return newchildren

def group_childrens( decls, parent = None ):
    if parent:
        if parent.kind == CursorKind.TRANSLATION_UNIT:
            return group_namespace( decls, parent )
        elif parent.kind == CursorKind.NAMESPACE:
            return group_namespace( decls, parent )
            return group_class( decls, parent )
        elif parent.kind == CursorKind.CLASS_DECL:
            return group_class( decls, parent )
        elif parent.kind == CursorKind.CLASS_TEMPLATE:
            return group_class( decls, parent )
        elif parent.kind == CursorKind.STRUCT_DECL:
            return group_class( decls, parent )
    return group_other( decls, parent )

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

def convert_to_nodes( decls, comments ):
    def cnvt_nodes( nodes, parent ):
        result = []
        for ( cursor, children ) in nodes:
            parent_link = parent['link']
            name = self_name( cursor.canonical )
            key = parent['key'] + [ name ]
            node = decl_node( key, name, cursor )
            if node:
                node['link'] = link_url( parent_link, node )
                if cursor in comments:
                    node['comments'] += comments[cursor]
                node['children'] = cnvt_nodes( children, node )
                if node['kind'] != 'group' or node['children']:
                    result.append( node )
        return result
    result = cnvt_nodes( decls, { 'key': [], 'link': '' } )
    return result
    
def assign_comments( decls, comments, mapping = {} ):
    result = {}
    top = decls[0][0]
    for ( tag, cmt, loc ) in comments:
        decl = top
        if tag == '!<' or tag == '<':
            decl = find_preceding_decl( top, decls, loc )
        else:
            decl = find_following_decl( top, decls, loc )
        key = decl.canonical
        lst = result.get( key, [] )
        lst.append( cmt )
        result[key] = lst
    return result

def remove_unused_access( tree, accesses ):
    result = []
    for ( cursor, children ) in tree:
        if cursor.kind == CursorKind.CXX_ACCESS_SPEC_DECL and cursor not in accesses:
            continue
        result.append( ( cursor, remove_unused_access( children, accesses ) ) )
    return result

def merge( master, more ):
    for ( name, comments ) in more.items():
        cmts = master.get( name, [] )
        cmts += comments
        master[name] = cmts

def merge_decl_tree( master, tree ):
    for node in tree:
        inmaster = next( filter( lambda x: x['name'] == node['name'], master ), None )
        if inmaster:
            #print( "MERGING " + inmaster['kind'] + ' ' + inmaster['name'] + ' ' + str(len( node['children'] ) )
            inmaster['comments'] += node['comments']
            inmaster['location'] += node['location']
            merge_decl_tree( inmaster['children'], node['children'] )
        else:
            inmaster = copy.deepcopy( node )
            #print( "APPENDING " + inmaster['kind'] + ' ' + inmaster['name'] )
            master.append( inmaster )

def dump_tree( tree, indent = 0 ):
    tabs = '  ' * indent
    for ( cursor, children ) in tree:
        ext = ( cursor.extent.start.offset, cursor.extent.end.offset )
        print( tabs + cursor.kind.name + ' ' + cursor.spelling + ' ' + str( ext ) )
        dump_tree( children, indent + 1 )

def dump_decl( decl ):
    ext = ( decl.extent.start.offset, decl.extent.end.offset )
    pprint( ( decl.spelling, ext ) )

def gather_comments( tu, files ):
    decl_cmts_list = []
    parents = {}
    for filename in files:
        print( "========== " + filename )
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
        #    pprint( ( sem_name( item[0] ), item[1] ) )
        #print( '----------' )

        access_comments = set( [c for c in decl_cmts if c.kind == CursorKind.CXX_ACCESS_SPEC_DECL] )
        #print( "ACCESS_COMMENTS", len( access_comments ) )
        tree = remove_unused_access( tree, set( access_comments ) )

        tree = group_childrens( tree )
        #print( "DECL_TREE GROUPED" )
        #dump_tree( tree )
        #print( '----------' )

        # Assign comments to declarations
        decl_cmts = convert_to_nodes( tree, decl_cmts )
        #print( "DECL_CMTS as NODES" )
        #pprint( decl_cmts, sort_dicts=False )
        #print( '----------' )

        # Finally add all of the decl_cmts2 into the final list
        merge_decl_tree( decl_cmts_list, decl_cmts )

    #print( "DECL_CMTS_LIST" )
    #pprint( decl_cmts_list, sort_dicts=False )
    #print( '----------' )

    return decl_cmts_list

