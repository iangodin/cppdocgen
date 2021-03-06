
import sqlite3
import yaml
import os
from pprint import pprint
from pathlib import Path
from cleanup import Cleanup
from jinja2 import Environment, FileSystemLoader, select_autoescape
from html import escape

order = [ "Template Parameters", "Namespaces", "Types", "Parameters", "Constructors", "Destructor", "Fields", "Public", "Methods", "Friends", "Protected" ]

def group_order( name ):
    try:
        return str( order.index( name ) )
    except:
        return name

def html_file( node ):
    link = node['link']
    assert '#' not in link, 'not an html file ' + link
    if link == '':
        return Path( 'index.html' )
    else:
        return Path( *(link.split( '/' )) )

def filter_kind( nodes, kind ):
    if isinstance( kind, str ):
        return filter( lambda n: kind == '' or n['kind'] == kind, nodes )
    else:
        return filter( lambda n: n['kind'] in kind, nodes )

def anchor( node ):
    result = None
    if '#' in node['link']:
        result = node['link'].split( '#' )[-1]
    return result

class HTMLGenerator:
    def __init__( self, dbfile, topdir ):
        self.topdir = topdir
        self.connection = sqlite3.connect( dbfile )
        self.cursor = self.connection.cursor()
        loc = os.path.join( os.path.dirname( os.path.realpath( __file__ ) ), "templates" )
        self.env = Environment(
            loader = FileSystemLoader( loc )
        )
        self.env.filters['filter_kind'] = filter_kind
        self.env.globals['list'] = list
        self.env.globals['anchor'] = anchor
        self.cleaner = Cleanup()

    def generate( self ):
        top = {
            'name': '',
            'link': '/index.html',
            'kind': 'global',
            'decl': '',
            'comments': '',
            'children': self.load_nodes(),
        }
        #pprint( top, sort_dicts=False )
        self.generate_node( top, [] )

    def load_nodes( self, parent = '' ):
        rows = self.cursor.execute( f'SELECT name, key, link, kind, decl, comments FROM nodes WHERE parent="{parent}";' ).fetchall();
        nodes = []
        for row in rows:
            child = { 'name': row[0], 'key': row[1], 'link': row[2], 'kind': row[3], 'decl': escape( row[4] ), 'comments': row[5] }
            child['comments'] = self.cleaner( child['comments'] )
            child['children'] = self.load_nodes( child['key'] )
            nodes.append( child )
        #nodes.sort( key=lambda n: group_order( n['name'] ) )
        return nodes

    def generate_node( self, node, parents ):
        for n in node['children']:
            if node['kind'] == 'group':
                self.generate_node( n, parents )
            else:
                self.generate_node( n, parents + [ node ] )

        if node['kind'] in [ 'class', 'struct', 'namespace', 'global' ]:
            filename = self.topdir / html_file( node )
            assert '#' not in str( filename ), 'expected class/struct/namespace/global without fragment'
            filename.parent.mkdir( parents = True, exist_ok = True )
            template = self.env.get_template( node['kind'] + ".html" )
            htmlData = template.render( node=node, parents=parents );
            with filename.open( 'w' ) as f:
                f.write( htmlData )

