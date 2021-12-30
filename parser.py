
from clang.cindex import AccessSpecifier, CursorKind, Cursor
from pathlib import Path, PosixPath
from pprint import pprint
from functools import reduce
import yaml

htmlTypes = [ 'global', 'class', 'struct', 'namespace' ]

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
            'auto_doc': [ '<p>Global namespaces, functions, classes, and variables.</p>' ],
            'user_doc': '',
            'parent': [],
            'link': 'index.html',
            'children': [],
        }

        lookup = {}
        lookup['global'] = top

        for node in parser.nodes:
            if node['kind'] != 'file':
                node['parent'][0] = 'global'
                pkey = '/'.join( node['parent'] )
                if pkey in lookup:
                    if node['kind'] in htmlTypes:
                        node['link'] = '/' + str( PosixPath( *node['parent'], node['name'] ).with_suffix( '.html' ) )
                    else:
                        node['link'] = '#' + node['name']
                    parent = lookup[pkey]

                    key = pkey + '/' + node['name']
                    dupnode = lookup.get( key, None )
                    if dupnode:
                        newnode = parser.merge_duplicate( dupnode, node )
                        lookup[key] = newnode
                    else:
                        parent['children'].append( node )
                        lookup[key] = node
                else:
                    pprint( pkey + " not found" )

        # Resolve duplicates
        for node in lookup.values():
            if node['kind'] == 'duplicate':
                pkey = '/'.join( node['parent'] )
                parent = lookup[pkey]

                overloads = {}
                dups = node['children']
                for n in dups:
                    t = n['type']
                    if t in overloads:
                        parser.merge_identical( overloads[t], n )
                    else:
                        overloads[t] = n.copy()
                node.clear();
                node.update( reduce( parser.merge_overload, overloads.values() ) )

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
                node['cursor_kind'] = str( cursor.kind )
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

    def access( parser, cursor ):
        a = cursor.access_specifier
        if a == AccessSpecifier.PUBLIC:
            return 'public'
        if a == AccessSpecifier.PROTECTED:
            return 'protected'
        if a == AccessSpecifier.PRIVATE:
            return 'private'
        return 'unknown'

    def merge_overload( self, overload, node ):
        overload['auto_doc'] += node['auto_doc']
        overload['user_doc'] += node['user_doc']
        return overload

    def merge_identical( self, overload, node ):
        if len( overload['user_doc'] ) < len( node['user_doc'] ):
            overload['user_doc'] = node['user_doc']
        return overload

    def merge_duplicate( self, node1, node2 ):
        duplicate = None
        if node1 == None:
            node1 = node2
        else:
            if node1['kind'] != 'duplicate':
                copy = node1.copy()
                node1.clear()
                node1.update( {
                    'kind': 'duplicate',
                    'name': copy['name'],
                    'parent': copy['parent'],
                    'link': copy['link'],
                    'children': [ copy, node2 ]
                } )
            else:
                node1['children'].append( node2 )
        return node1

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
        return result

    def FUNCTION_TEMPLATE( parser, cursor ):
        comments = parser.gather_comments( cursor )
        kind = 'function'
        parent = cursor.semantic_parent

        # Is there a more reliable way to tell if a template is a constructor?
        # But this should work well enough
        if parent.kind in [ CursorKind.CLASS_DECL, CursorKind.STRUCT_DECL, CursorKind.CLASS_TEMPLATE ]:
            if cursor.spelling == parent.displayname:
                kind = 'constructor'
            else:
                kind = 'method'

        result = {
            'kind': kind,
            'name': cursor.spelling,
            'parent': parser.get_parent( cursor ),
            'link': None,
            'group': parser.group,
            'comments': comments,
            'type': cursor.type.spelling,
            'result': cursor.result_type.spelling if kind != 'constructor' else '',
            'templates': [],
            'params': [],
            'children': [],
        }
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

    def COMPOUND_STMT( parser, cursor ):
        return None
