
from clang.cindex import AccessSpecifier, CursorKind
from pathlib import Path
from pprint import pprint
import yaml

def get_info(node, depth=0):
    if depth < 3:
        children = [get_info(c, depth+1)
                    for c in node.get_children()]
    else:
        children = None
    return { 'kind' : str( node.kind ),
             'spelling' : node.spelling,
             'displayname' : node.displayname,
             'type' : node.type.spelling,
             'location' : str( node.location ),
             'children' : children }

def compare_location( loc1, loc2 ):
    if loc1.line < loc2.line:
        return True
    if loc1.line == loc2.line:
        return loc1.column < loc2.column
    return False

class Parser:
    def __init__( parser, topdir ):
        parser.group = None
        parser.warned = set()
        parser.topdir = topdir

    def __call__( parser, node ):
        if node.location.file != None and parser.topdir not in Path( str( node.location.file ) ).resolve().parents:
            return None
        k = node.kind.name
        method = getattr( Parser, k, None )
        if method == None:
            method = Parser.unknown
        n = method( parser, node )
        if n != None and n['kind'] != 'group' and parser.group != None:
            g = parser.group['group']
            g.append( n )
            if len( g ) == 1:
                n = parser.group
            else:
                n = None
        return n

    def begin_group( parser, comments ):
        name = comments[0].lstrip( '/' );
        name = name.strip();
        parser.group = {
            'kind': 'group',
            'name': name,
            'comments': comments[1:],
            'group': [],
        }

    def gather_comments( parser, node ):
        result = []
        if node.raw_comment != None:
            result = list( map( str.lstrip, node.raw_comment.splitlines() ) )
        return result

    def end_group( parser ):
        parser.group = None

    def unknown( parser, node ):
        if node.kind.name not in parser.warned:
            print( "unknown node type " + node.kind.name )
        parser.warned.add( node.kind.name )
        return {
            'kind': 'unknown',
            'name': node.spelling,
            'info': str( node.kind.name ),
            'location': node.location,
        }

    def decls( parser, node ):
        return list( filter( None, map( parser, node.get_children() ) ) )

    def arguments( parser, node ):
        return list( filter( None, map( parser, filter( lambda n: n.kind == CursorKind.PARM_DECL, node.get_children() ) ) ) )

    def templates( parser, node ):
        def is_template( node ):
            return node.kind == CursorKind.TEMPLATE_TYPE_PARAMETER or node.kind == CursorKind.TEMPLATE_NON_TYPE_PARAMETER
        return list( filter( None, map( parser, filter( is_template, node.get_children() ) ) ) )

    def compound( parser, node, is_template ):
        parents = []
        members = []
        templates = []
        for child in node.get_children():
            c = parser( child )
            if c == None:
                continue
            if c['kind'] == 'parent':
                parents.append( c )
            elif c['kind'] == 'template':
                templates.append( c )
            else:
                members.append( c )
        tmps = { 'templates': templates } if is_template else {}
        return { 'parents': parents, 'members': members } | tmps

    def access( parser, node ):
        a = node.access_specifier
        if a == AccessSpecifier.PUBLIC:
            return 'public'
        if a == AccessSpecifier.PROTECTED:
            return 'protected'
        if a == AccessSpecifier.PRIVATE:
            return 'private'
        return 'unknown'

    def TRANSLATION_UNIT( parser, node ):
        result = {
            'kind': 'file',
            'name': node.spelling,
            'declarations': parser.decls( node )
        }
        parser.end_group()
        return result

    def NAMESPACE( parser, node ):
        comments = parser.gather_comments( node )
        prev_group = parser.group
        parser.group = None
        result = {
            'kind': 'namespace',
            'name': node.spelling,
            'comments': comments,
            'declarations': parser.decls( node )
        }
        parser.group = prev_group
        return result

    def VAR_DECL( parser, node ):
        comments = parser.gather_comments( node )
        prev_group = parser.group
        parser.group = None
        result = {
            'kind': 'variable',
            'name': node.spelling,
            'type': node.type.spelling,
            'comments': comments
        }
        parser.group = prev_group
        return result

    def CLASS_TEMPLATE( parser, node ):
        return parser.CLASS_DECL( node, True )

    def CLASS_DECL( parser, node, is_template = False ):
        comments = parser.gather_comments( node )
        prev_group = parser.group
        parser.group = None
        result = {
            'kind': 'class',
            'name': node.spelling,
            'comments': comments
        } | parser.compound( node, is_template )
        parser.group = prev_group
        return result

    def STRUCT_DECL( parser, node ):
        result = parser.CLASS_DECL( node )
        result['kind'] = 'struct'
        return result

    def CXX_BASE_SPECIFIER( parser, node ):
        result = {
            'kind': 'parent',
            'name': node.spelling,
            'access': parser.access( node )
        }
        return result

    def CXX_ACCESS_SPEC_DECL( parser, node ):
        # Ignore public:/protected:/private: access.
        # Each member is tagged with access already.
        if node.raw_comment != None:
            comments = parser.gather_comments( node )
            parser.begin_group( comments )
        return None

    def CXX_METHOD( parser, node ):
        if node.lexical_parent.kind.name != 'CLASS_DECL':
            return None
        comments = parser.gather_comments( node )
        prev_group = parser.group
        parser.group = None
        result = {
            'kind': 'method',
            'name': node.spelling,
            'comments': comments,
            'type': node.type.spelling,
            'access': parser.access( node ),
            'result': node.result_type.spelling,
            'arguments': [parser( a ) for a in node.get_arguments()],
        }
        parser.group = prev_group
        return result

    def CONSTRUCTOR( parser, node ):
        result = parser.CXX_METHOD( node )
        if result:
            result['kind'] = 'constructor'
        return result

    def FIELD_DECL( parser, node ):
        comments = parser.gather_comments( node )
        prev_group = parser.group
        parser.group = None
        result = {
            'kind': 'field',
            'name': node.spelling,
            'comments': comments,
            'type': node.type.spelling,
            'access': parser.access( node ),
        }
        parser.group = prev_group
        return result

    def FRIEND_DECL( parser, node ):
        friend = parser( next( node.get_children() ) )
        comments = parser.gather_comments( node )
        prev_group = parser.group
        parser.group = None
        result = {
            'kind': 'friend',
            'name': friend['name'],
            'comments': comments,
            'friend': friend,
            'access': parser.access( node ),
        }
        parser.group = prev_group
        return result

    def TYPE_REF( parser, node ):
        return {
            'kind': 'type',
            'name': node.type.spelling,
            'type': node.spelling,
        }

    def PARM_DECL( parser, node ):
        return {
            'kind': 'param',
            'name': node.spelling,
            'type': node.type.spelling,
        }

    def FUNCTION_TEMPLATE( parser, node ):
        result = parser.FUNCTION_DECL( node )
        result['templates'] = parser.templates( node )
        return result

    def FUNCTION_DECL( parser, node ):
        comments = parser.gather_comments( node )
        prev_group = parser.group
        parser.group = None
        result = {
            'kind': 'function',
            'name': node.spelling,
            'comments': comments,
            'type': node.type.spelling,
            'result': node.result_type.spelling,
            'arguments': parser.arguments( node ),
        }
        parser.group = prev_group
        return result

    def TEMPLATE_TYPE_PARAMETER( parser, node ):
        result = {
            'kind': 'template',
            'name': node.spelling,
            'comments': [],
            'type': next( node.get_tokens() ).spelling,
        }
        return result

    def TEMPLATE_NON_TYPE_PARAMETER( parser, node ):
        result = {
            'kind': 'template',
            'name': node.spelling,
            'comments': [],
            'type': node.type.spelling,
        }
        return result

    def TYPE_ALIAS_DECL( parser, node ):
        comments = parser.gather_comments( node )
        prev_group = parser.group
        parser.group = None
        result = {
            'kind': 'typedef',
            'name': node.spelling,
            'comments': comments,
            'type': node.underlying_typedef_type.spelling,
        }
        parser.group = prev_group
        return result
