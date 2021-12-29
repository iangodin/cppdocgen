
from clang.cindex import AccessSpecifier, CursorKind, Cursor
from pathlib import Path, PosixPath
from pprint import pprint
import yaml

htmlTypes = [ 'global', 'class', 'struct', 'namespace' ]

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
        parser.nodes = []
        parser.cursors = set()
        parser.params = None
        parser.templates = None
        parser.type = None

    def __call__( parser, cursor ):
        assert False, 'not here'

    def create_tree( parser ):
        top = {
            'kind': 'global',
            'name': 'global',
            'parent': [],
            'link': 'index.html',
            'children': [],
        }

        lookup = {}

        for node in parser.nodes:
            if node['kind'] == 'file':
                lookup[node['name']] = top
            else:
                key = '/'.join( node['parent'] )
                if key in lookup:
                    node['parent'][0] = 'global'
                    if node['kind'] in htmlTypes:
                        node['link'] = str( PosixPath( *node['parent'], node['name'] ).with_suffix( '.html' ) )
                    else:
                        node['link'] = str( PosixPath( *node['parent'] ).with_suffix( '.html' ) ) + '#' + node['name']
                    parent = lookup[key]
                    parent['children'].append( node )
                    lookup[key + '/' + node['name']] = node
                else:
                    print( "??????????????" )
                    pprint( node, sort_dicts=False )
                    print( "??????????????" )
        return top


    def parse( parser, cursor ):
        if cursor.location.file != None and parser.topdir not in Path( str( cursor.location.file ) ).resolve().parents:
            return None
        k = cursor.kind.name
        method = getattr( Parser, k, Parser.UNKNOWN )
        if cursor.hash not in parser.cursors:
            saved_group = parser.group
            node = method( parser, cursor )
            parser.cursors.add( cursor.hash )
            if node != None:
                parser.nodes.append( node );
                for c in cursor.get_children():
                    parser.parse( c )
                if parser.params != None:
                    if 'params' in node:
                        node['params'] = parser.params
                        parser.params = None
                if parser.templates != None:
                    if 'templates' in node:
                        node['templates'] = parser.templates
                        parser.templates = None
                if node['kind'] != 'group':
                    parser.group = saved_group

    def add_param( parser, param ):
        if parser.params == None:
            parser.params = []
        parser.params.append( param )

    def add_template( parser, tmp ):
        if parser.templates == None:
            parser.templates = []
        parser.templates.append( tmp )

    def get_parent( parser, cursor ):
        chain = []
        p = cursor.semantic_parent
        while isinstance( p, Cursor ):
            chain.append( p.spelling )
            p = p.semantic_parent
        chain.reverse()
        return chain

    def gather_comments( parser, node ):
        result = []
        if node.raw_comment != None:
            result = list( map( str.lstrip, node.raw_comment.splitlines() ) )
        return result

    def UNKNOWN( parser, cursor ):
        if cursor.kind.name not in parser.warned:
            print( "unknown node type " + cursor.kind.name )
        parser.warned.add( cursor.kind.name )
        node = {
            'kind': 'unknown',
            'name': cursor.spelling,
            'parent': parser.get_parent( cursor ),
            'link': None,
            'info': str( cursor.kind.name ),
            'location': cursor.location,
            'children': [],
        }
        # TODO should we process children of unknown??
        return node

    def convert_decl( parser, cursor, node ):
        if not cursor.is_definition():
            node['decl_kind'] = node['kind']
            node['kind'] = 'decl'

    def access( parser, cursor ):
        a = cursor.access_specifier
        if a == AccessSpecifier.PUBLIC:
            return 'public'
        if a == AccessSpecifier.PROTECTED:
            return 'protected'
        if a == AccessSpecifier.PRIVATE:
            return 'private'
        return 'unknown'

    def TRANSLATION_UNIT( parser, cursor ):
        result = {
            'kind': 'file',
            'name': cursor.spelling,
            'parent': parser.get_parent( cursor ),
            'link': None,
            'children': []
        }
        return result

    def NAMESPACE( parser, cursor ):
        comments = parser.gather_comments( cursor )
        result = {
            'kind': 'namespace',
            'name': cursor.spelling,
            'parent': parser.get_parent( cursor ),
            'link': None,
            'comments': comments,
            'children': []
        }
        return result

    def VAR_DECL( parser, cursor ):
        comments = parser.gather_comments( cursor )
        result = {
            'kind': 'variable',
            'name': cursor.spelling,
            'parent': parser.get_parent( cursor ),
            'link': None,
            'group': parser.group,
            'type': cursor.type.spelling,
            'comments': comments
        }
        return result

    def CLASS_DECL( parser, cursor, is_template = False ):
        comments = parser.gather_comments( cursor )
        parser.group = None
        result = {
            'kind': 'class',
            'name': cursor.spelling,
            'parent': parser.get_parent( cursor ),
            'link': None,
            'comments': comments,
            'parents': [],
            'children': [],
        }
        parser.convert_decl( cursor, result )
        return result

    def CLASS_TEMPLATE( parser, cursor ):
        comments = parser.gather_comments( cursor )
        parser.group = None
        result = {
            'kind': 'class',
            'name': cursor.spelling,
            'parent': parser.get_parent( cursor ),
            'link': None,
            'comments': comments,
            'parents': [],
            'templates': [],
            'children': [],
        }
        parser.convert_decl( cursor, result )
        return result


    def STRUCT_DECL( parser, cursor ):
        comments = parser.gather_comments( cursor )
        parser.group = None
        result = {
            'kind': 'struct',
            'name': cursor.spelling,
            'parent': parser.get_parent( cursor ),
            'link': None,
            'comments': comments,
            'parents': [],
            'children': [],
        }
        parser.convert_decl( cursor, result )
        return result

    def CXX_BASE_SPECIFIER( parser, cursor ):
        result = {
            'kind': 'parent',
            'name': cursor.spelling,
            'parent': parser.get_parent( cursor ),
            'link': None,
            'access': parser.access( cursor ),
            'children': [],
        }
        return result

    def CXX_ACCESS_SPEC_DECL( parser, cursor ):
        # Each member is tagged with access already.
        if cursor.raw_comment != None:
            comments = parser.gather_comments( cursor )
            name = comments[0].lstrip( '/' );
            name = name.strip();
            result = {
                'kind': 'group',
                'name': name,
                'parent': parser.get_parent( cursor ),
                'link': None,
                'comments': comments[1:],
                'children': [],
            }
            parser.group = name
            return result
        return None

    def CXX_METHOD( parser, cursor ):
        comments = parser.gather_comments( cursor )
        result = {
            'kind': 'method',
            'name': cursor.spelling,
            'parent': parser.get_parent( cursor ),
            'link': None,
            'group': parser.group,
            'comments': comments,
            'type': cursor.type.spelling,
            'access': parser.access( cursor ),
            'result': cursor.result_type.spelling,
            'params': [],
            'children': [],
        }
        return result

    def CONSTRUCTOR( parser, cursor ):
        result = parser.CXX_METHOD( cursor )
        if result:
            result['result'] = ''
            result['kind'] = 'constructor'
        return result

    def DESTRUCTOR( parser, cursor ):
        result = parser.CXX_METHOD( cursor )
        if result:
            result['result'] = ''
            result['kind'] = 'destructor'
        return result

    def FIELD_DECL( parser, cursor ):
        comments = parser.gather_comments( cursor )
        result = {
            'kind': 'field',
            'name': cursor.spelling,
            'parent': parser.get_parent( cursor ),
            'link': None,
            'group': parser.group,
            'comments': comments,
            'type': cursor.type.spelling,
            'access': parser.access( cursor ),
            'children': [],
        }
        return result

    def FRIEND_DECL( parser, cursor ):
        comments = parser.gather_comments( cursor )
        result = {
            'kind': 'friend',
            'name': friend['name'],
            'parent': parser.get_parent( cursor ),
            'link': None,
            'comments': comments,
            'access': parser.access( cursor ),
            'children': [],
        }
        return result

    def TYPE_REF( parser, cursor ):
        #print( "TYPE_REF: " + cursor.spelling + ' ' + cursor.type.spelling )
        return None

    def PARM_DECL( parser, cursor ):
        result = {
            'kind': 'param',
            'name': cursor.spelling,
            'type': cursor.type.spelling,
            'children': [],
        }
        parser.add_param( result )
        return None

    def FUNCTION_DECL( parser, cursor ):
        comments = parser.gather_comments( cursor )
        result = {
            'kind': 'function',
            'name': cursor.spelling,
            'parent': parser.get_parent( cursor ),
            'link': None,
            'group': parser.group,
            'comments': comments,
            'type': cursor.type.spelling,
            'result': cursor.result_type.spelling,
            'params': [],
            'children': [],
        }
        parser.convert_decl( cursor, result )
        return result

    def FUNCTION_TEMPLATE( parser, cursor ):
        comments = parser.gather_comments( cursor )
        result = {
            'kind': 'function',
            'name': cursor.spelling,
            'parent': parser.get_parent( cursor ),
            'link': None,
            'group': parser.group,
            'comments': comments,
            'type': cursor.type.spelling,
            'result': cursor.result_type.spelling,
            'templates': [],
            'params': [],
            'children': [],
        }
        parser.convert_decl( cursor, result )
        return result


    def TEMPLATE_TYPE_PARAMETER( parser, cursor ):
        result = {
            'kind': 'template',
            'name': cursor.spelling,
            'parent': parser.get_parent( cursor ),
            'link': None,
            'comments': [],
            'type': ' '.join( [t.spelling for t in cursor.get_tokens() if t.spelling != cursor.spelling] ),
            'children': [],
        }
        parser.convert_decl( cursor, result )
        parser.add_template( result )
        return None

    def TEMPLATE_NON_TYPE_PARAMETER( parser, cursor ):
        result = {
            'kind': 'template',
            'name': cursor.spelling,
            'parent': parser.get_parent( cursor ),
            'link': None,
            'comments': [],
            'type': cursor.type.spelling,
            'children': [],
        }
        parser.convert_decl( cursor, result )
        parser.add_template( result )
        return None

    def TYPE_ALIAS_DECL( parser, cursor ):
        comments = parser.gather_comments( cursor )
        result = {
            'kind': 'typedef',
            'name': cursor.spelling,
            'parent': parser.get_parent( cursor ),
            'link': None,
            'group': parser.group,
            'comments': comments,
            'type': cursor.underlying_typedef_type.spelling,
            'children': [],
        }
        return result

    def NAMESPACE_REF( parser, cursor ):
        #print( "NAMESPACE_REF: " + cursor.spelling )
        return None
