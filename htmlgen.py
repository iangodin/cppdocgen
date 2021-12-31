
import sqlite3
import yaml
from pprint import pprint
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

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
        self.env = Environment(
            loader = FileSystemLoader( "templates" )
        )
        self.env.filters['filter_kind'] = filter_kind
        self.env.globals['list'] = list
        self.env.globals['anchor'] = anchor

    def generate( self ):
        tops = self.load_nodes()
        assert len( tops ) == 1, 'expect only one global node'
        tops[0]['name'] = ''
        self.generate_node( tops[0], [] )

    def load_nodes( self, parent_id = 0 ):
        rows = self.cursor.execute( f'SELECT id, name, kind, link, user, auto FROM nodes WHERE parent_id={parent_id} ORDER BY id;' ).fetchall();
        nodes = []
        for row in rows:
            child = { 'id': row[0], 'name': row[1], 'kind': row[2], 'link': row[3], 'user': row[4], 'auto': row[5] }
            child['children'] = self.load_nodes( child['id'] )
            nodes.append( child )
        return nodes

    def generate_node( self, node, parents ):
        for n in node['children']:
            if node['kind'] == 'group':
                self.generate_node( n, parents )
            else:
                self.generate_node( n, parents + [ node ] )

        if node['kind'] in [ 'class', 'struct', 'namespace', 'global' ]:
            filename = self.topdir / Path( *node['link'].split( '/' ) )
            assert '#' not in str( filename ), 'expected class/struct/namespace/global without fragment'
            filename.parent.mkdir( parents = True, exist_ok = True )
            template = self.env.get_template( node['kind'] + ".html" )
            htmlData = template.render( node=node, parents=parents );
            with filename.open( 'w' ) as f:
                f.write( htmlData )

